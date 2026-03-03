"""
SQLAlchemy ORM table definitions for RAG document chunking and embedding tables.

Defines table mapping, chunk metadata, and embedding tables for chunked
retrieval-augmented generation (RAG) workflows in the genomicsdb ragdoc schema.
"""

from niagads.genomicsdb.schema.admin.mixins import TableRefMixin
from niagads.genomicsdb.schema.ragdoc.base import RAGDocTableBase
from pgvector.sqlalchemy import Vector
from sqlalchemy import (
    TEXT,
    ForeignKey,
    Index,
    Integer,
    LargeBinary,
    String,
    UniqueConstraint,
)
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.ext.hybrid import hybrid_property


class ChunkMetadata(RAGDocTableBase, TableRefMixin):
    """
    Stores chunk boundaries and metadata for structured and unstructured documents.
    """

    __tablename__ = "chunkmetadata"
    __table_args__ = (
        UniqueConstraint(
            "table_id",
            "row_id",
            "section",
            "chunk_index",
            "chunk_hash",
            name="uq_chunk_metadata",
        ),
        Index("ix_chunkmetadata_table_doc", "table_id", "row_id"),
        Index("ix_chunkmetadata_chunk_hash", "chunk_hash"),  # for checking staleness
    )

    chunk_metadata_id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    chunk_hash: Mapped[bytes] = mapped_column(LargeBinary(32), nullable=False)

    section: Mapped[str] = mapped_column(
        String(64), nullable=False, server_default="FULL"
    )
    chunk_index: Mapped[int] = mapped_column(Integer, nullable=True)
    start_offset: Mapped[int] = mapped_column(Integer, nullable=True)
    end_offset: Mapped[int] = mapped_column(Integer, nullable=True)
    chunk_text: Mapped[str] = mapped_column(TEXT, nullable=True)
    doc_hash: Mapped[bytes] = mapped_column(LargeBinary(32), nullable=True)

    @hybrid_property
    def chunk_id(self):
        return f"{self.section}_{self.chunk_index}"

    @chunk_id.expression
    def chunk_id(cls):
        return f"{cls.section}_{cls.chunk_index}"


class ChunkEmbedding(RAGDocTableBase):
    """
    Stores vector embeddings for document chunks, linked to chunk metadata.
    """

    __tablename__ = "chunkembedding"
    __table_args__ = (
        UniqueConstraint(
            "chunk_metadata_id",
            "model_id",
            "chunk_hash",
            name="uq_embedding_chunk",
        ),
        Index("ix_embedding_vector_hnsw", "embedding", postgresql_using="hnsw"),
        Index("ix_chunkembedding_chunk_hash", "chunk_hash"),  # for checking staleness
    )

    embedding_id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    chunk_metadata_id: Mapped[int] = mapped_column(
        ForeignKey("ragdoc.chunkmetadata.chunk_metadata_id"), nullable=False, index=True
    )
    model_id: Mapped[str] = mapped_column(String(100), nullable=False, index=True)
    chunk_hash: Mapped[bytes] = mapped_column(LargeBinary(32), nullable=False)
    embedding: Mapped[list[float]] = mapped_column(Vector(384), nullable=False)
