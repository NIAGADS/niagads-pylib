"""
SQLAlchemy ORM table definitions for RAG document chunking and embedding tables.

Defines table mapping, chunk metadata, and embedding tables for chunked
retrieval-augmented generation (RAG) workflows in the genomicsdb ragdoc schema.
"""

from niagads.genomicsdb.schema.ragdoc.base import RAGDocSchemaBase
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


class TableMap(RAGDocSchemaBase):
    """
    Maps logical document sources to table and schema names for RAG workflows.
    """

    __tablename__ = "tablemap"
    __table_args__ = (
        UniqueConstraint("schema_name", "table_name", name="uq_schema_table_pair"),
    )
    table_id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    schema_name: Mapped[str] = mapped_column(String(50), index=True)
    table_name: Mapped[str] = mapped_column(String(50), index=True)


class ChunkMetadata(RAGDocSchemaBase):
    """
    Stores chunk boundaries and metadata for structured and unstructured documents.
    """

    __tablename__ = "chunkmetadata"
    __table_args__ = (
        UniqueConstraint(
            "table_id", "doc_id", "chunk_id", "chunk_hash", name="uq_chunk_metadata"
        ),
        Index("ix_chunkmetadata_table_doc", "table_id", "doc_id"),
        Index("ix_chunkembedding_chunk_hash", "chunk_hash"),  # for checking staleness
    )

    chunk_metadata_id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    table_id: Mapped[int] = mapped_column(
        ForeignKey("ragdoc.tablemap.table_id"), nullable=False, index=True
    )
    doc_id: Mapped[int] = mapped_column(Integer, nullable=False, index=True)
    chunk_hash: Mapped[bytes] = mapped_column(LargeBinary(32), nullable=False)

    section: Mapped[str] = mapped_column(
        String(64), nullable=False, server_default="FULL"
    )
    chunk_index: Mapped[int] = mapped_column(Integer, nullable=True)
    start_offset: Mapped[int] = mapped_column(Integer, nullable=True)
    end_offset: Mapped[int] = mapped_column(Integer, nullable=True)
    chunk_text: Mapped[str] = mapped_column(TEXT, nullable=True)
    doc_hash: Mapped[bytes] = mapped_column(LargeBinary(32), nullable=True)

    def chunk_id(self):
        return f"{self.section}_{self.chunk_index}"


class ChunkEmbedding(RAGDocSchemaBase):
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
