""" "create larger embedding fields"

Revision ID: 12dcb65f0992
Revises: 84fb2087ecf7
Create Date: 2026-10-13 22:39:53.069536

"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from pgvector.sqlalchemy import Vector

# revision identifiers, used by Alembic.
revision: str = "12dcb65f0992"
down_revision: Union[str, None] = "84fb2087ecf7"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.alter_column(
        "chunkembedding",
        "embedding",
        new_column_name="embedding_old",
        existing_type=Vector(384),
        existing_nullable=True,
        schema="ragdoc",
    )
    op.add_column(
        "chunkembedding",
        sa.Column("embedding", Vector(1024), nullable=True),
        schema="ragdoc",
    )
    op.drop_index(
        "ix_ragdoc_chunkembedding_embedding",
        table_name="chunkembedding",
        schema="ragdoc",
    )
    op.create_index(
        "ix_ragdoc_chunkembedding_embedding",
        "chunkembedding",
        ["embedding"],
        schema="ragdoc",
        postgresql_using="hnsw",
        postgresql_ops={"embedding": "vector_cosine_ops"},
    )


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_index(
        "ix_ragdoc_chunkembedding_embedding",
        table_name="chunkembedding",
        schema="ragdoc",
    )
    op.drop_column("chunkembedding", "embedding", schema="ragdoc")
    op.alter_column(
        "chunkembedding",
        "embedding_old",
        new_column_name="embedding",
        existing_type=Vector(384),
        existing_nullable=True,
        schema="ragdoc",
    )
    op.create_index(
        "ix_ragdoc_chunkembedding_embedding",
        "chunkembedding",
        ["embedding"],
        schema="ragdoc",
        postgresql_using="hnsw",
        postgresql_ops={"embedding": "vector_cosine_ops"},
    )
