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

import asyncio
import json
import os
from datetime import datetime

from niagads.common.core import ComponentBaseMixin
from niagads.database.genomicsdb.schema.ragdoc.chunks import (
    ChunkEmbedding,
    ChunkMetadata,
)
from niagads.database.session import DatabaseSessionManager
from niagads.nlp.embeddings import TextEmbeddingGenerator
from niagads.nlp.llm_types import LLM
from sqlalchemy import select, text


class EmbeddingPatch(ComponentBaseMixin):
    """Load stored chunk metadata for the embedding patch."""

    def __init__(self, database_uri: str):
        super().__init__()
        self._database_uri = database_uri
        self._chunk_metadata: list[ChunkMetadata]
        self._embedding_generator = TextEmbeddingGenerator(LLM.BGE_M3)
        self._embedding_counter = 0
        self._new_metadata_count = 0 


    def _serialize_json_value(self, value) -> str:
        """Serialize JSON compactly for storage and token counting."""
        return json.dumps(value, sort_keys=True, separators=(",", ":"))

    def _is_within_embedding_limit(self, value) -> bool:
        """Return whether a JSON value fits the embedding model input limit."""
        return self._embedding_generator.token_count(
            self._serialize_json_value(value)
        ) <= self._embedding_generator.max_sequence_length

    def _split_json_value(self, value, metadata: ChunkMetadata) -> list:
        """Split a JSON value into model-sized values without changing its type."""
        if self._is_within_embedding_limit(value):
            return [value]

        if isinstance(value, list):
            chunks = []
            current_chunk = []
            for item in value:
                for item_chunk in self._split_json_value(item, metadata):
                    candidate = current_chunk + [item_chunk]
                    if current_chunk and not self._is_within_embedding_limit(candidate):
                        chunks.append(current_chunk)
                        current_chunk = [item_chunk]
                    else:
                        current_chunk = candidate
            if current_chunk:
                chunks.append(current_chunk)
            return chunks

        if isinstance(value, dict):
            for key, child_value in value.items():
                if not self._is_within_embedding_limit(child_value):
                    return [
                        {**value, key: child_chunk}
                        for child_chunk in self._split_json_value(
                            child_value, metadata
                        )
                    ]

            chunks = []
            current_chunk = {}
            for key, child_value in value.items():
                candidate = {**current_chunk, key: child_value}
                if current_chunk and not self._is_within_embedding_limit(candidate):
                    chunks.append(current_chunk)
                    current_chunk = {key: child_value}
                else:
                    current_chunk = candidate
            if current_chunk:
                chunks.append(current_chunk)
            return chunks

        token_count = self._embedding_generator.token_count(
            self._serialize_json_value(value)
        )
        overflow = token_count - self._embedding_generator.max_sequence_length
        self.logger.warning(
            f"JSON chunk cannot be split below the BGE-M3 token limit; it has "
            f"{token_count} tokens, exceeding the limit by {overflow}. Human "
            f"review of the loading plugin is required. "
            f"table_id={metadata.table_id} row_id={metadata.row_id} "
            f"chunk_text={metadata.chunk_text!r}"
        )
        return []

    def _build_chunk_metadata(
        self, metadata: ChunkMetadata, chunk_values: list
    ) -> list[ChunkMetadata]:
        """Create metadata rows for recursively split JSON values."""
        chunks = []
        for index, value in enumerate(chunk_values):
            chunk_text = self._serialize_json_value(value)
            chunks.append(
                ChunkMetadata(
                    table_id=metadata.table_id,
                    row_id=metadata.row_id,
                    document_type=metadata.document_type,
                    document_section=metadata.document_section,
                    document_hash=metadata.document_hash,
                    chunk_hash=self._embedding_generator.hash_text(chunk_text),
                    chunk_text=chunk_text,
                    chunk_index=metadata.chunk_index + index,
                    start_offset=metadata.start_offset,
                    end_offset=metadata.end_offset,
                    run_id=metadata.run_id,
                )
            )
        return chunks

    def _chunk_document(self, metadata: ChunkMetadata) -> list[ChunkMetadata]:
        """Split oversized JSON while retaining its parent object structure."""
        document = json.loads(metadata.chunk_text)
        return self._build_chunk_metadata(
            metadata, self._split_json_value(document, metadata)
        )


    async def _update_chunk_embeddings(self, session, metadata: ChunkMetadata):
        """Re-embed a chunk when its text fits the BGE-M3 input window."""

        token_count = self._embedding_generator.token_count(metadata.chunk_text)
        if token_count <= self._embedding_generator.max_sequence_length:
            embedding = self._embedding_generator.generate(metadata.chunk_text)
            chunk_embedding = ChunkEmbedding(
                chunk_metadata_id=metadata.chunk_metadata_id,
                chunk_hash=metadata.chunk_hash,
                embedding_model=str(LLM.BGE_M3),
                embedding=embedding,
                embedding_date=datetime.now(),
            )
            await chunk_embedding.submit(session)
            self._embedding_counter += 1

            self.logger.info(
                f"Re-embedded chunk metadata {metadata.chunk_metadata_id} "
                f"using BGE-M3 ({token_count} tokens)."
            )
        
        else:
            chunks = self._chunk_document(metadata)
            # insert new chunks
            # delete original chunk 
            # calculate and load embeddings for all new chunks 
 


    async def _retrieve_chunk_metadata(self, session):
        stmt = select(ChunkMetadata)
        self._chunk_metadata = (await session.execute(stmt)).scalars().all()
        session.expunge_all()
        self.logger.info(
            f"Retrieved {len(self._chunk_metadata)} chunk metadata records."
        )

    async def run(self) -> None:
        """Retrieve all chunk metadata and retain it after closing the session."""
        manager = DatabaseSessionManager(self._database_uri)
        try:
            async with manager.session_ctx() as session:
                await self._retrieve_chunk_metadata(session)
                for chunk_metadata in self._chunk_metadata:
                    await self._update_chunk_embeddings(session, chunk_metadata)

        finally:
            await manager.close()


if __name__ == "__main__":
    patch = EmbeddingPatch(os.environ["DATABASE_URI"])
    asyncio.run(patch.run())
