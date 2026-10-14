#!/usr/bin/env python

"""
patch embeddings to use BGE-M3 and larger embedding vector field

I think what we want to do is actually truncate ragdoc.chunkmedata -> delete it all
(assume this is done outside of this patch)

then iterate over ragdoc.chunkmetadata

- calculate token size for each chunk text
--> if fits limit, embed
--> if not leverage chunk_index, start_offset, end_offset to create new entries for further chunking
    -> calculate and load new embeddings for new metadata
    --> delete old metadata
"""

import argparse
import asyncio
import json
import os
from datetime import datetime
from typing import Iterator, Optional
import logging

from niagads.common.types import ETLOperation, ProcessStatus
from niagads.common.core import ComponentBaseMixin
from niagads.database.genomicsdb.schema.admin.etl import ETLRun
from niagads.database.genomicsdb.schema.ragdoc.chunks import (
    ChunkEmbedding,
    ChunkMetadata,
)
from niagads.database.session import DatabaseSessionManager
from niagads.nlp.embeddings import TextEmbeddingGenerator
from niagads.nlp.llm_types import LLM
from niagads.utils.list import chunker
from pydantic import BaseModel
from sqlalchemy import select


class DocumentChunk(BaseModel):
    chunk_text: str
    chunk_index: Optional[int] = None
    offset_start: Optional[int] = None
    offset_end: Optional[int] = None


class EmbeddingPatch(ComponentBaseMixin):
    """Load stored chunk metadata for the embedding patch."""

    def __init__(self, database_uri: str, force_cpu: bool = False):
        super().__init__()
        self._database_uri = database_uri
        self._chunk_metadata: list[ChunkMetadata]
        self._embedding_generator = TextEmbeddingGenerator(
            LLM.BGE_M3, force_cpu=force_cpu
        )
        self._embedding_counter = 0
        self._new_metadata_count = 0
        self._run_id: Optional[int] = None
        self._batch_size = 512

        self._new_chunk_embeddings: list = []

        self.logger.setLevel(logging.INFO)

    async def _create_etl_run(self, session):
        etl_run = ETLRun(
            plugin_name="patch-embeddings",
            plugin_version="1.0",
            params={"embedding_model": str(LLM.BGE_M3)},
            message="Embedding patch initiated",
            status=ProcessStatus.IN_PROGRESS,
            operation=str(ETLOperation.UPDATE),
            start_time=datetime.now(),
            rows_processed=0,
            is_test_run=False,
        )
        self._run_id = await etl_run.submit(session)

    def _serialize_json_value(self, value) -> str:
        """Serialize JSON compactly for storage and token counting."""
        return json.dumps(value, sort_keys=True, separators=(",", ":"))

    def _chunk_text_document(document):
        raise NotImplementedError("Not sure if we need this")

    def _chunk_list(self, item, index: int):

        key, list_values = next(iter(item.items()))
        current_chunk = []
        empty_chunk_token_count = self._embedding_generator.token_count(
            self._serialize_json_value({key: []})
        )
        current_token_count = empty_chunk_token_count
        next_index = 0 if index is None else index + 1

        for value in list_values:
            value_token_count = self._embedding_generator.token_count(
                self._serialize_json_value(value)
            )
            if (
                current_chunk
                and current_token_count + value_token_count
                > self._embedding_generator.max_sequence_length
            ):
                yield DocumentChunk(
                    chunk_text=self._serialize_json_value({key: current_chunk}),
                    chunk_index=next_index,
                )
                next_index += 1
                current_chunk = []
                current_token_count = empty_chunk_token_count

            current_chunk.append(value)
            current_token_count += value_token_count

        if current_chunk:
            yield DocumentChunk(
                chunk_text=self._serialize_json_value({key: current_chunk}),
                chunk_index=next_index,
            )

    def _chunk_json_value(self, value, index: int = None):
        """Split a JSON value into model-sized values without changing its type."""

        json_str = self._serialize_json_value(value)
        token_count = self._embedding_generator.token_count(json_str)

        if token_count <= self._embedding_generator.max_sequence_length:
            yield DocumentChunk(
                chunk_text=json_str,
                chunk_index=index,
            )
            return

        current_chunk = {}
        current_token_count = 0
        next_index = 0 if index is None else index + 1
        oversized_items = []

        for key, child_value in value.items():
            item = {key: child_value}
            item_token_count = self._embedding_generator.token_count(
                self._serialize_json_value(item)
            )

            if item_token_count > self._embedding_generator.max_sequence_length:
                oversized_items.append(item)
                continue

            if (
                current_chunk
                and current_token_count + item_token_count
                > self._embedding_generator.max_sequence_length
            ):
                yield DocumentChunk(
                    chunk_text=self._serialize_json_value(current_chunk),
                    chunk_index=next_index,
                )
                next_index += 1
                current_chunk = item
                current_token_count = item_token_count
            else:
                current_chunk.update(item)
                current_token_count += item_token_count

        if current_chunk:
            yield DocumentChunk(
                chunk_text=self._serialize_json_value(current_chunk),
                chunk_index=next_index,
            )
            next_index += 1

        # handle oversized items
        for oversized_item in oversized_items:
            value = next(iter(oversized_item.values()))
            if isinstance(
                value, str
            ):  # nothing we can do about this here, it will be truncated
                yield DocumentChunk(
                    chunk_text=self._serialize_json_value(oversized_item),
                    chunk_index=next_index,
                )
                next_index += 1
            if isinstance(value, dict):
                # not sure if this will happen. need to see
                raise ValueError(f"oversized nested dict: {value}")
            if isinstance(value, list):
                for chunk in self._chunk_list(oversized_item, next_index):
                    yield chunk
                    next_index = chunk.chunk_index + 1

    def _chunk_document(self, metadata: ChunkMetadata) -> Iterator[DocumentChunk]:
        """Split oversized JSON while retaining its parent object structure."""
        try:
            document = json.loads(metadata.chunk_text)
            return self._chunk_json_value(document)

        except (TypeError, json.JSONDecodeError):
            return self._chunk_text_document(metadata.chunk_text)

    async def _update_chunk_embeddings(self, session, metadata: ChunkMetadata):
        """Re-embed a chunk when its text fits the BGE-M3 input window."""

        token_count = self._embedding_generator.token_count(metadata.chunk_text)
        if token_count <= self._embedding_generator.max_sequence_length:
            self._new_chunk_embeddings.append(
                {
                    "chunk_embedding": ChunkEmbedding(
                        chunk_metadata_id=metadata.chunk_metadata_id,
                        chunk_hash=metadata.chunk_hash,
                        embedding_model=str(LLM.BGE_M3),
                        embedding_date=datetime.now(),
                        modification_date=datetime.now(),
                        run_id=self._run_id,
                        embedding_run_id=self._run_id,
                    ),
                    "chunk_text": metadata.chunk_text,
                }
            )

        else:
            chunks = self._chunk_document(metadata)
            for chunk in chunks:
                chunk_metadata = ChunkMetadata(
                    table_id=metadata.table_id,
                    row_id=metadata.row_id,
                    document_type=metadata.document_type,
                    document_section=metadata.document_section,
                    document_hash=metadata.document_hash,
                    chunk_hash=self._embedding_generator.hash_text(chunk.chunk_text),
                    chunk_text=chunk.chunk_text,
                    chunk_index=chunk.chunk_index,
                    run_id=self._run_id,
                )
                chunk_metadata_id = await chunk_metadata.submit(session)
                self._new_chunk_embeddings.append(
                    {
                        "chunk_embedding": ChunkEmbedding(
                            chunk_metadata_id=chunk_metadata_id,
                            chunk_hash=chunk_metadata.chunk_hash,
                            embedding_model=str(LLM.BGE_M3),
                            embedding_date=datetime.now(),
                            run_id=self._run_id,
                            embedding_run_id=self._run_id,
                        ),
                        "chunk_text": chunk_metadata.chunk_text,
                    }
                )
                self._new_metadata_count += 1

            # delete original
            await session.delete(metadata)

    async def _finalize_etl_run(self, session, status, message):
        etl_run = await session.get(ETLRun, self._run_id)
        etl_run.status = status
        etl_run.end_time = datetime.now()
        etl_run.rows_processed = self._new_metadata_count + self._embedding_counter
        etl_run.message = message

    async def _retrieve_chunk_metadata(self, session):
        stmt = select(ChunkMetadata)
        self._chunk_metadata = (await session.execute(stmt)).scalars().all()
        session.expunge_all()
        self.logger.info(
            f"Retrieved {len(self._chunk_metadata)} chunk metadata records."
        )

    async def run(self, commit: bool = False) -> None:
        """Retrieve all chunk metadata and retain it after closing the session."""
        manager = DatabaseSessionManager(self._database_uri)
        try:
            async with manager.session_ctx() as session:
                await self._create_etl_run(session)
                status = ProcessStatus.SUCCESS
                message = "Embedding patch completed"
                try:
                    self.logger.info("retrieving data")
                    await self._retrieve_chunk_metadata(session)
                    self.logger.info(f"retrived {len(self._chunk_metadata)} records")

                    self.logger.info("updating metadata")
                    for index, chunk_metadata in enumerate(
                        self._chunk_metadata, start=1
                    ):
                        await self._update_chunk_embeddings(session, chunk_metadata)

                    self.logger.info("Done generating updated metadata.")
                    self.logger.info(
                        f"{len(self._new_chunk_embeddings)} new embeddings to be generated."
                    )

                    embedding_list_chunker = chunker(
                        self._new_chunk_embeddings, self._batch_size
                    )
                    for elindex, elchunk in enumerate(embedding_list_chunker, start=1):
                        self.logger.info(f"Generating embeddings for chunk {elindex}")
                        embeddings = self._embedding_generator.generate(
                            [item["chunk_text"] for item in elchunk], as_list=True
                        )
                        self._embedding_counter += len(elchunk)
                        for cindex, item in enumerate(elchunk):
                            chunk_embedding: ChunkEmbedding = item["chunk_embedding"]
                            chunk_embedding.embedding = embeddings[cindex]
                            await chunk_embedding.submit(session)

                        self.logger.info(
                            f"Updated {self._embedding_counter} embeddings"
                        )
                except Exception as error:
                    status = ProcessStatus.FAIL
                    message = str(error)
                    raise
                finally:
                    await self._finalize_etl_run(session, status, message)
                    if commit:
                        await session.commit()
                    else:
                        await session.rollback()

        finally:
            await manager.close()


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--force-cpu",
        action="store_true",
        help="Run embedding generation on the CPU.",
    )
    parser.add_argument(
        "--commit",
        action="store_true",
        help="Commit the embedding patch changes.",
    )
    args = parser.parse_args()

    patch = EmbeddingPatch(os.environ["DATABASE_URI"], force_cpu=args.force_cpu)
    asyncio.run(patch.run(commit=args.commit))
