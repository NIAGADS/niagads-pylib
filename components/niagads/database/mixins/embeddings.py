"""
EmbeddingMixin for vector search tables in GenomicsDB.

Defines reusable ORM fields and index utilities for storing and searching vector embeddings
using pgvector and HNSW indexes. Includes embedding metadata, model tracking, and ETL run linkage.
"""

from datetime import datetime

from niagads.database.helpers import datetime_column
from niagads.genomicsdb.schema.admin.helpers import etlrun_fk_column
from pgvector.sqlalchemy import Vector
from sqlalchemy import Index, LargeBinary, String
from sqlalchemy.orm import Mapped, mapped_column


class EmbeddingMixin:
    __abstract__ = True

    embedding: Mapped[list[float]] = mapped_column(Vector(384), nullable=True)
    embedding_model: Mapped[str] = mapped_column(String(250), nullable=True, index=True)
    embedding_hash: Mapped[bytes] = mapped_column(LargeBinary(32), nullable=True)
    embedding_date: Mapped[datetime] = datetime_column(nullable=True)
    embedding_run_id: Mapped[int] = etlrun_fk_column(nullable=True)

    @classmethod
    def get_indexes(
        cls, schema: str, table: str, embedding_type: str = "vector_cosine_ops"
    ):
        """
        Generate HNSW vector index for embedding column.

        Creates a PostgreSQL HNSW (Hierarchical Navigable Small World) index
        for efficient similarity search on the embedding vector column.

        Args:
            schema: Database schema name (for index naming).
            table: Table name (for index naming).
            embedding_type: PostgreSQL vector operation class (default: "vector_cosine_ops"
                for cosine similarity). Can be "vector_l2_ops" for L2 distance or
                "vector_ip_ops" for inner product.

        Returns:
            Tuple containing a single Index object configured for HNSW search.
        """
        id = f"ix_{schema}_{table}_embedding"
        return (
            Index(
                id,
                "embedding",
                postgresql_using="hnsw",
                postgresql_ops={"embedding": embedding_type},
            ),
        )
