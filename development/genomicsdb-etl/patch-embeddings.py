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
from typing import Optional

from niagads.common.core import ComponentBaseMixin
from niagads.database.genomicsdb.schema.ragdoc.chunks import (
    ChunkEmbedding,
    ChunkMetadata,
)
from niagads.database.session import DatabaseSessionManager
from niagads.nlp.embeddings import TextEmbeddingGenerator
from niagads.nlp.llm_types import LLM
from pydantic import BaseModel, Field
from sqlalchemy import select


class DocumentChunk(BaseModel):
    chunk_text: str
    chunk_index: Optional[int] = None
    offset_start: Optional[int] = None
    offset_end: Optional[int] = None


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

    def _chunk_text_document(document): ...

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

        if isinstance(value, dict):
            _item_sizes = {
                key: self._embedding_generator.token_count(
                    self._serialize_json_value({key: child_value})
                )
                for key, child_value in value.items()
            }

        # handle json

        # unresolvable message
        overflow = token_count - self._embedding_generator.max_sequence_length
        self.logger.warning(
            f"JSON chunk cannot be split below the BGE-M3 token limit; it has "
            f"{token_count} tokens, exceeding the limit by {overflow}."
        )
        self.logger.info(f"chunk_text={value!r}")
        return []

    def _chunk_document(self, metadata: ChunkMetadata) -> list[ChunkMetadata]:
        """Split oversized JSON while retaining its parent object structure."""
        try:
            document = json.loads(metadata.chunk_text)
            return self._chunk_json_value(document)

        except (TypeError, json.JSONDecodeError):
            return self._chunk_text_document(document)

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
            chunks: list[DocumentChunk] = self._chunk_document(metadata)
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
