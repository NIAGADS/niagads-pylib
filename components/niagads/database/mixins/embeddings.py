from datetime import datetime

from niagads.database.mixins.columns import datetime_column
from pgvector import Vector
from sqlalchemy import ForeignKey, Index, LargeBinary, String
from sqlalchemy.orm import Mapped, mapped_column


class EmbeddingMixin:
    __table_args__ = (
        Index("ix_embedding_vector_hnsw", "embedding", postgresql_using="hnsw"),
    )

    embedding: Mapped[list[float]] = mapped_column(Vector(384), nullable=True)
    embedding_model: Mapped[str] = mapped_column(String(250), nullable=True, index=True)
    embedding_hash: Mapped[bytes] = mapped_column(LargeBinary(32), nullable=True)
    embedding_date: Mapped[datetime] = datetime_column(nullable=True)
    embedding_run_id: Mapped[int] = mapped_column(
        ForeignKey("admin.etlrun.etl_run_id"), nullable=True, index=True
    )
