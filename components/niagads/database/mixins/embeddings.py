from datetime import datetime

from niagads.database.helpers import datetime_column
from niagads.genomicsdb.schema.admin.helpers import etlrun_fk_column
from pgvector.sqlalchemy import Vector
from sqlalchemy import Index, LargeBinary, String
from sqlalchemy.orm import Mapped, mapped_column


class EmbeddingMixin:

    embedding: Mapped[list[float]] = mapped_column(Vector(384), nullable=True)
    embedding_model: Mapped[str] = mapped_column(String(250), nullable=True, index=True)
    embedding_hash: Mapped[bytes] = mapped_column(LargeBinary(32), nullable=True)
    embedding_date: Mapped[datetime] = datetime_column(nullable=True)
    embedding_run_id: Mapped[int] = etlrun_fk_column(nullable=True)

    @classmethod
    def get_indexes(cls, schema: str, table: str):
        """Return only the Index objects for __table_args__"""

        id = f"ix_{schema}_{table}_embedding"
        return (
            Index(
                id,
                "embedding",
                postgresql_using="hnsw",
                postgresql_ops={"embedding": "vector_cosine_ops"},
            ),
        )
