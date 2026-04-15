""" "change rexp for ensembl source id format checks"

Revision ID: f6c9bb8e3bb8
Revises: 92f691d5d7d8
Create Date: 2026-04-05 22:53:31.238480

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

import niagads.database.decorators
import pgvector.sqlalchemy.vector
import sqlalchemy_utils.types.ltree

# revision identifiers, used by Alembic.
revision: str = "f6c9bb8e3bb8"
down_revision: Union[str, None] = "92f691d5d7d8"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    # Drop old check constraints
    op.drop_constraint(
        "gene_source_id_format_check", "gene", type_="check", schema="gene"
    )
    op.drop_constraint(
        "transcript_source_id_format_check", "transcript", type_="check", schema="gene"
    )
    op.drop_constraint(
        "exon_source_id_format_check", "exon", type_="check", schema="gene"
    )

    # Add new check constraints (regex patterns must match the new model)
    op.create_check_constraint(
        "gene_source_id_format_check",
        "gene",
        r"source_id ~ '^ENSG[0-9]+$'",
        schema="gene",
    )
    op.create_check_constraint(
        "transcript_source_id_format_check",
        "transcript",
        r"source_id ~ '^ENST[0-9]+$'",
        schema="gene",
    )
    op.create_check_constraint(
        "exon_source_id_format_check",
        "exon",
        r"source_id ~ '^ENSE[0-9]+$'",
        schema="gene",
    )


def downgrade() -> None:
    """Downgrade schema."""
    # Drop new check constraints
    op.drop_constraint(
        "gene_source_id_format_check", "gene", type_="check", schema="gene"
    )
    op.drop_constraint(
        "transcript_source_id_format_check", "transcript", type_="check", schema="gene"
    )
    op.drop_constraint(
        "exon_source_id_format_check", "exon", type_="check", schema="gene"
    )

    # Recreate old check constraints (replace with previous regex if needed)
    op.create_check_constraint(
        "gene_source_id_format_check",
        "gene",
        r"source_id ~ '^ENSG[0-9]{11}$'",
        schema="gene",
    )
    op.create_check_constraint(
        "transcript_source_id_format_check",
        "transcript",
        r"source_id ~ '^ENST[0-9]{11}$'",
        schema="gene",
    )
    op.create_check_constraint(
        "exon_source_id_format_check",
        "exon",
        r"source_id ~ '^ENSE[0-9]{11}$'",
        schema="gene",
    )
