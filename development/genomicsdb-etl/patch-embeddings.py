#!/usr/bin/env python

"""
patch embeddings to use BGE-M3 and larger embedding vector field

RAGDoc.Embedding is truncated before this is run - old embeddings are irrelvant and non-existant for this patch
 note - rollback logic is flawed but not really used at runtime+

"""

import argparse
import asyncio
import json
import logging
import os
from datetime import datetime
from typing import Iterator, Optional

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
from niagads.utils.logging import ExitOnExceptionHandler
from niagads.utils.string import truncate_tokens
from pydantic import BaseModel
from sqlalchemy import select

EMBEDDING_MODEL = LLM.LFM2_5_EMBEDDING_350M


class DocumentChunk(BaseModel):
    chunk_text: str
    chunk_index: Optional[int] = None
    offset_start: Optional[int] = None
    offset_end: Optional[int] = None


class EmbeddingPatch(ComponentBaseMixin):
    """Load stored chunk metadata for the embedding patch."""

    SOFT_TOKEN_LIMIT = 400
    HARD_TOKEN_MARGIN = 20

    def __init__(
        self, database_uri: str, force_cpu: bool = False, batch_size: int = 128
    ):
        super().__init__()
        self._database_uri = database_uri
        self._chunk_metadata: list[ChunkMetadata]

        self._embedding_generator = TextEmbeddingGenerator(
            EMBEDDING_MODEL, force_cpu=force_cpu
        )
        self._hard_token_limit = (
            self._embedding_generator.max_sequence_length - self.HARD_TOKEN_MARGIN
        )
        self._embedding_counter = 0
        self._new_metadata_count = 0
        self._run_id: Optional[int] = None
        self._batch_size = batch_size

        self._new_chunk_embeddings: list = []
        self._new_chunk_metadata: list[ChunkMetadata] = []
        self._chunk_metadata_to_delete: list[ChunkMetadata] = []

        self.logger.setLevel(logging.INFO)

    async def _create_etl_run(self, session):
        etl_run = ETLRun(
            plugin_name="patch-embeddings",
            plugin_version="1.0",
            params={"embedding_model": str(EMBEDDING_MODEL)},
            message="Embedding patch initiated",
            status=ProcessStatus.IN_PROGRESS,
            operation=str(ETLOperation.UPDATE),
            start_time=datetime.now(),
            rows_processed=0,
            is_test_run=False,
        )
        self._run_id = await etl_run.submit(session)
        await session.commit()  # always commit

    def _serialize_json_value(self, value) -> str:
        """Serialize JSON compactly for storage and token counting."""
        return json.dumps(value, sort_keys=True, separators=(",", ":"))

    def _chunk_text_document(self, document: str):
        """Convert ontology term text to JSON before applying structured chunking."""
        if not document.startswith("Term:"):
            raise NotImplementedError(
                "Text chunking is only implemented for ontology terms."
            )

        parsed_document = {}
        last_key = None
        for line in document.splitlines():
            key, separator, value = line.partition(":")
            if not separator:
                if last_key is None:
                    raise ValueError(f"Unable to parse ontology term line: {line}")
                parsed_document[last_key] += f" {line.strip()}"
                continue

            key = key.strip()
            value = value.lstrip().replace("\n", " ")
            if key == "Definition" and value == "None":
                last_key = key
                continue
            if key == "Synonym":
                parsed_document.setdefault(key, []).append(value)
            else:
                parsed_document[key] = value
            last_key = key

        return self._chunk_json_value(parsed_document)

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

            # if single list element is oversized, we need to truncate it
            if isinstance(value, str) and value_token_count > self.SOFT_TOKEN_LIMIT:
                value = truncate_tokens(
                    value,
                    self._embedding_generator.tokenizer,
                    self.SOFT_TOKEN_LIMIT,
                )
                value_token_count = self._embedding_generator.token_count(
                    self._serialize_json_value(value)
                )
            if (
                current_chunk
                and current_token_count + value_token_count > self._hard_token_limit
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

        if token_count <= self.SOFT_TOKEN_LIMIT:
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

            if item_token_count > self._hard_token_limit:
                oversized_items.append(item)
                continue

            if (
                current_chunk
                and current_token_count + item_token_count > self.SOFT_TOKEN_LIMIT
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

    def _embedding_batches(self):
        """Yield embedding batches sized for both count and token length."""
        batch = []
        largest_token_count = 0

        for item in self._new_chunk_embeddings:
            token_count = item["token_count"]
            proposed_largest = max(largest_token_count, token_count)
            # Limit batch count based on the largest item while allowing one item
            # through when its token count exceeds the effective hard limit.
            token_batch_size = max(1, self._hard_token_limit // proposed_largest)
            allowed_batch_size = min(self._batch_size, token_batch_size)

            if batch and len(batch) >= allowed_batch_size:
                yield batch
                batch = []
                largest_token_count = 0

            batch.append(item)
            largest_token_count = max(largest_token_count, token_count)

        if batch:
            yield batch

    def _chunk_existing_metadata(self, metadata: ChunkMetadata):
        """chunk existing metadata it does not fit the input window."""

        token_count = self._embedding_generator.token_count(metadata.chunk_text)
        is_ontology_term = metadata.chunk_text.startswith("Term:")

        if token_count <= self.SOFT_TOKEN_LIMIT and not is_ontology_term:
            self._new_chunk_embeddings.append(
                {
                    "chunk_embedding": ChunkEmbedding(
                        chunk_metadata_id=metadata.chunk_metadata_id,
                        chunk_hash=metadata.chunk_hash,
                        embedding_model=str(EMBEDDING_MODEL),
                        embedding_date=datetime.now(),
                        modification_date=datetime.now(),
                        run_id=self._run_id,
                        embedding_run_id=self._run_id,
                    ),
                    "chunk_text": metadata.chunk_text,
                    "token_count": token_count,
                }
            )

        else:
            chunks = self._chunk_document(metadata)
            for chunk in chunks:
                token_count = self._embedding_generator.token_count(chunk.chunk_text)
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
                self._new_chunk_metadata.append(chunk_metadata)
                self._new_chunk_embeddings.append(
                    {
                        "chunk_metadata": chunk_metadata,
                        "chunk_text": chunk_metadata.chunk_text,
                        "token_count": token_count,
                    }
                )
                self._new_metadata_count += 1

            self._chunk_metadata_to_delete.append(metadata)

    async def _finalize_etl_run(self, session, status, message):
        etl_run = await session.get(ETLRun, self._run_id)
        etl_run.status = status
        etl_run.end_time = datetime.now()
        etl_run.rows_processed = len(self._new_chunk_metadata) + len(
            self._new_chunk_embeddings
        )
        etl_run.message = message
        await session.commit()

    async def _retrieve_chunk_metadata(self, session):
        stmt = select(ChunkMetadata)
        self._chunk_metadata = (await session.execute(stmt)).scalars().all()
        session.expunge_all()
        self.logger.info(
            f"Retrieved {len(self._chunk_metadata)} chunk metadata records."
        )

    def _duplicate_sanity_check(self):
        self.logger.info("Duplicate sanity Check")
        from collections import Counter

        keys = [(m.table_id, m.row_id, m.chunk_text) for m in self._new_chunk_metadata]

        duplicates = {key: count for key, count in Counter(keys).items() if count > 1}

        if duplicates:
            raise ValueError(
                f"Duplicate generated metadata based on chunk_text: {duplicates}"
            )
        else:
            keys = [
                (m.table_id, m.row_id, m.chunk_hash, m.chunk_index)
                for m in self._new_chunk_metadata
            ]
            duplicates = {
                key: count for key, count in Counter(keys).items() if count > 1
            }
            if duplicates:
                raise ValueError(
                    f"Duplicate generated metadata based on integrity key {duplicates}"
                )
        self.logger.info("No duplicates found")

    async def _delete_obsolete(self, session, commit: bool):
        message_prefix = "COMMIT" if commit else "ROLLBACK"
        self.logger.info("Removing obsolete metadata entries.")
        transaction_count = 0
        for metadata in self._chunk_metadata_to_delete:
            current_id = metadata.chunk_metadata_id
            await session.delete(metadata)
            transaction_count += 1
            if transaction_count % 25000 == 0:
                if commit:
                    await session.commit()
                else:
                    await session.rollback()
                self.logger.info(
                    f"{message_prefix}: Deleted {transaction_count} obsolete metadata entries. Checkpoint: chunk_metadata_id={current_id}"
                )

        # residuals
        if commit:
            await session.commit()
        else:
            await session.rollback()
        self.logger.info(
            f"{message_prefix}: Deleted {transaction_count} obsolete metadata entries."
        )

    async def run(self, commit: bool = False) -> None:
        """Retrieve all chunk metadata and retain it after closing the session."""
        self._commit = commit
        message_prefix = "COMMIT" if commit else "ROLLBACK"
        transaction_count = 0
        manager = DatabaseSessionManager(self._database_uri, expire_on_commit=False)
        try:
            async with manager.session_ctx() as session:
                await self._create_etl_run(session)
                status = ProcessStatus.SUCCESS
                message = "Embedding patch completed"
                try:
                    self.logger.info("Fetching database records")
                    await self._retrieve_chunk_metadata(session)

                    self.logger.info("Generating and chunking metadata")
                    for index, chunk_metadata in enumerate(
                        self._chunk_metadata, start=1
                    ):
                        self._chunk_existing_metadata(chunk_metadata)
                        if index % 10000 == 0:
                            self.logger.info(f"Generated {index} metadata entries.")

                    self.logger.info("Done generating and chunking metadata.")

                    self._duplicate_sanity_check()
                    await self._delete_obsolete(session, commit)

                    self.logger.info("Inserting new metadata records.")
                    if self._new_chunk_metadata:
                        chunked_list = chunker(
                            self._new_chunk_metadata, 25000
                        )
                        for c in chunked_list:
                            await ChunkMetadata.submit_many(session, c)
                            checkpoint_id = c[-1].chunk_metadata_id
                            if commit:
                                await session.commit()
                            else:
                                await session.rollback()
                            transaction_count += len(c)
                            self.logger.info(
                                f"{message_prefix}: {transaction_count} metadata entries. Checkpoint: chunk_metadata_id={checkpoint_id}"
                            )
                    self.logger.info(
                        f"{message_prefix}: {transaction_count} metadata entries. Checkpoint: chunk_metadata_id={checkpoint_id}"
                    )

                    self.logger.info("Generating new embedding placeholders")
                    num_placeholders = 0
                    for item in self._new_chunk_embeddings:
                        chunk_embedding = item.get("chunk_embedding", None)
                        if not chunk_embedding:
                            chunk_metadata = item["chunk_metadata"]
                            item["chunk_embedding"] = ChunkEmbedding(
                                chunk_metadata_id=chunk_metadata.chunk_metadata_id,
                                chunk_hash=chunk_metadata.chunk_hash,
                                embedding_model=str(EMBEDDING_MODEL),
                                embedding_date=datetime.now(),
                                run_id=self._run_id,
                                embedding_run_id=self._run_id,
                            )
                            num_placeholders += 1
                        if num_placeholders % 25000 == 0:
                            self.logger.info(f"Generated {num_placeholders} embedding placeholders.")
                            
                    self.logger.info(f"Generated {num_placeholders} embedding placeholders.")

                    num_embeddings = 0
                    for elindex, elchunk in enumerate(
                        self._embedding_batches(), start=1
                    ):
                        # self.logger.info(f"Generating embeddings for chunk {elindex}")
                        embeddings = self._embedding_generator.generate(
                            [item["chunk_text"] for item in elchunk],
                            as_list=True,
                            prompt_name="document",
                        )

                        chunk_embeddings: list[ChunkEmbedding] = []
                        for cindex, item in enumerate(elchunk):
                            chunk_embedding: ChunkEmbedding = item["chunk_embedding"]
                            chunk_embedding.embedding = embeddings[cindex]
                            chunk_embeddings.append(chunk_embedding)
                            num_embeddings += 1
                            
                        await ChunkEmbedding.submit_many(session, chunk_embeddings)
                        checkpoint_id = chunk_embeddings[-1].chunk_embedding_id
                        
                        if num_embeddings % 1000 == 0:
                            self.logger.info(f"Inserted {num_embeddings} chunk embeddings. Checkpoint: chunk_embedding_id={checkpoint_id}")
                            if commit:
                                await session.commit()
                            else:
                                await session.rollback()
                                
                    # residuals
                    if commit:
                        await session.commit()
                    else:
                        await session.rollback()
                    self.logger.info(
                        f"{message_prefix}: Inserted {len(elchunk)} chunk embeddings. Checkpoint: chunk_embedding_id={checkpoint_id}"
                    )

                except Exception as error:
                    status = ProcessStatus.FAIL
                    message = str(error)
                    raise
                finally:
                    await self._finalize_etl_run(session, status, message)

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
    parser.add_argument(
        "--batch-size",
        type=int,
        default=128,
        help="Number of texts to embed in each batch.",
    )
    parser.add_argument(
        "--log-file",
        default="patch-embeddings.log",
        help="File to which the patch log is written.",
    )
    args = parser.parse_args()

    patch = EmbeddingPatch(
        os.environ["DATABASE_URI"],
        force_cpu=args.force_cpu,
        batch_size=args.batch_size,
    )
    patch.logger.handlers.clear()
    patch.logger.addHandler(ExitOnExceptionHandler(filename=args.log_file, mode="w"))
    patch.logger.propagate = False
    asyncio.run(patch.run(commit=args.commit))
