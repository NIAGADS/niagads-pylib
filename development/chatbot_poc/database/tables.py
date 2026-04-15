from niagads.database.helpers import datetime_column, enum_column, enum_constraint
from niagads.database.mixins.chunks import ChunkMetadataMixin
from niagads.database.mixins.embeddings import EmbeddingMixin
from niagads.database.types import RAGDocType, RetrievalStatus
from sqlalchemy import (
    ForeignKey,
    Index,
    Integer,
    LargeBinary,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


class RAGDeclarativeBase(DeclarativeBase):
    pass


class Document(RAGDeclarativeBase):
    """
    Source document tracked by the chatbot POC ingestion pipeline.
    """

    __tablename__ = "document"
    __table_args__ = (
        UniqueConstraint("url", "content_hash", name="uq_document_url_content_hash"),
        enum_constraint("document_type", RAGDocType),
        enum_constraint("retrieval_status", RetrievalStatus),
    )

    document_id: Mapped[int] = mapped_column(
        primary_key=True,
        autoincrement=True,
        comment="Stable document key used by chunk and retrieval records.",
    )
    url: Mapped[str] = mapped_column(
        String(2048),
        nullable=False,
        index=True,
        comment="Canonical source location for citation and re-fetch.",
    )
    document_type: Mapped[str] = enum_column(
        RAGDocType,
        nullable=False,
        index=True,
        comment="Identifies how the source should be interpreted during ingestion.",
    )
    content_hash: Mapped[bytes] = mapped_column(
        LargeBinary(32),
        nullable=False,
        comment="Detects when source content has changed across retrieval runs.",
    )
    retrieval_ts: Mapped[str] = datetime_column(nullable=True)
    retrieval_status: Mapped[str] = enum_column(
        RetrievalStatus,
        nullable=False,
        index=True,
        comment="Indicates the current retrieval or ingestion outcome for the document.",
    )


class IngestionJob(RAGDeclarativeBase):
    """Queued website ingestion request tracked by the admin app and worker."""

    __tablename__ = "ingestionjob"
    __table_args__ = (
        enum_constraint("status", RetrievalStatus),
        Index("ix_ingestionjob_status_created", "status", "creation_date"),
    )

    ingestion_job_id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    url: Mapped[str] = mapped_column(
        String(2048),
        nullable=False,
        index=True,
        comment="Root URL to crawl when the job is processed.",
    )
    max_pages: Mapped[int] = mapped_column(
        Integer,
        nullable=True,
        comment="Optional crawl limit applied to this job.",
    )
    status: Mapped[str] = enum_column(
        RetrievalStatus,
        nullable=False,
        index=True,
        comment="Current processing status for the ingestion job.",
    )
    creation_date: Mapped[str] = datetime_column(nullable=False)
    start_date: Mapped[str] = datetime_column(nullable=True)
    end_date: Mapped[str] = datetime_column(nullable=True)
    error_message: Mapped[str] = mapped_column(
        Text,
        nullable=True,
        comment="Failure details for the most recent processing attempt.",
    )
    num_documents: Mapped[int] = mapped_column(
        Integer,
        nullable=True,
        comment="Number of persisted documents created by the job.",
    )
    num_chunks: Mapped[int] = mapped_column(
        Integer,
        nullable=True,
        comment="Number of chunks created by the job.",
    )
    num_embeddings: Mapped[int] = mapped_column(
        Integer,
        nullable=True,
        comment="Number of embeddings created by the job.",
    )


class ChunkMetadata(RAGDeclarativeBase, ChunkMetadataMixin):
    __tablename__ = ChunkMetadataMixin.__tablename__
    __table_args__ = (ChunkMetadataMixin.__table_args__,)

    document_id: Mapped[int] = mapped_column(
        ForeignKey("document.document_id"),
        nullable=False,
        index=True,
        comment="Links each chunk back to the parent source document.",
    )


class ChunkEmbedding(RAGDeclarativeBase, EmbeddingMixin):
    __tablename__ = "chunkembedding"
    __table_args__ = (
        Index(
            "ix_chunkembedding_embedding",
            "embedding",
            postgresql_using="hnsw",
            postgresql_ops={"embedding": "vector_cosine_ops"},
        ),
        UniqueConstraint(
            "chunk_metadata_id",
            "embedding_model",
            "chunk_hash",
            name="uq_chunkembedding_chunk_model_hash",
        ),
        Index("ix_chunkembedding_chunk_hash", "chunk_hash"),
    )

    chunk_embedding_id: Mapped[int] = mapped_column(
        primary_key=True, autoincrement=True
    )
    chunk_metadata_id: Mapped[int] = mapped_column(
        ForeignKey("chunkmetadata.chunk_metadata_id"),
        nullable=False,
        index=True,
        comment="Links the embedding record to the chunk it was generated from.",
    )
    chunk_hash: Mapped[bytes] = mapped_column(
        LargeBinary(32),
        nullable=False,
        comment="Tracks which chunk content version this embedding represents.",
    )
