"""
SQLAlchemy ORM table definitions for RAG document chunking and embedding tables.

Defines table mapping, chunk metadata, and embedding tables for chunked
retrieval-augmented generation (RAG) workflows in the genomicsdb ragdoc schema.
"""

from niagads.database.genomicsdb.schema.admin.mixins import TableRefMixin
from niagads.database.genomicsdb.schema.ragdoc.base import RAGDocTableBase
from niagads.database.helpers import enum_column
from niagads.database.mixins.chunks import ChunkMetadataMixin
from niagads.database.mixins.embeddings import EmbeddingMixin
from niagads.database.types import RAGDocType
from sqlalchemy import ForeignKey, Index, LargeBinary, UniqueConstraint, event
from sqlalchemy.orm import Mapped, mapped_column


class ChunkMetadata(RAGDocTableBase, ChunkMetadataMixin, TableRefMixin):
    """
    Stores chunk boundaries and metadata for structured and unstructured documents.
    """

    __tablename__ = "chunkmetadata"
    __table_args__ = (
        *ChunkMetadataMixin.__table_args__,
        UniqueConstraint(
            "table_id",
            "row_id",
            "document_section",
            "chunk_index",
            "chunk_hash",
            name="uq_chunk_metadata",
        ),
        Index("ix_chunkmetadata_table_doc", "table_id", "row_id"),
        Index("ix_chunkmetadata_chunk_hash", "chunk_hash"),  # for checking staleness
        RAGDocTableBase.__table_args__,
    )
    document_type: Mapped[str] = enum_column(RAGDocType, nullable=False, index=True)


@event.listens_for(ChunkMetadata, "before_insert")
def generate_chunk_id(mapper, connection, target: ChunkMetadata):
    """
    SQLAlchemy event listener that generates chunk_id before inserting a ChunkMetadata record.

    This listener constructs a composite chunk_id from document_type, document_section,
    and chunk_index.

    usage:

    """
    if not target.document_section:
        target.document_section = "FULL"
    if not target.chunk_index:
        target.chunk_index = 0
    if not target.chunk_id:
        target.chunk_id = (
            f"{target.document_type}_{target.document_section }_{target.chunk_index}"
        )


class ChunkEmbedding(RAGDocTableBase, EmbeddingMixin):
    """
    Stores vector embeddings for document chunks, linked to chunk metadata.
    """

    __tablename__ = "chunkembedding"
    __table_args__ = (
        *EmbeddingMixin.get_indexes(RAGDocTableBase._schema, __tablename__),
        UniqueConstraint(
            "chunk_metadata_id",
            "embedding_model",
            "chunk_hash",
            name="uq_embedding_chunk",
        ),
        Index("ix_chunkembedding_chunk_hash", "chunk_hash"),  # for checking staleness
        RAGDocTableBase.__table_args__,
    )

    chunk_embedding_id: Mapped[int] = mapped_column(
        primary_key=True, autoincrement=True
    )
    chunk_metadata_id: Mapped[int] = mapped_column(
        ForeignKey("ragdoc.chunkmetadata.chunk_metadata_id"), nullable=False, index=True
    )
    chunk_hash: Mapped[bytes] = mapped_column(LargeBinary(32), nullable=False)
