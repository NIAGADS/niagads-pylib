"""
Base classes and helpers for SQLAlchemy ORM models in the genomicsdb gene schema.

Defines declarative base classes, metadata mixins, and foreign key helpers for gene-related tables.
"""

from niagads.genomicsdb.schema.bases import (
    DeclarativeMaterializedViewBase,
    DeclarativeTableBase,
)
from sqlalchemy import ForeignKey, Integer, MetaData
from sqlalchemy.orm import Mapped, mapped_column


def gene_fk_column(nullable: bool = False, index: bool = True) -> Mapped[int]:
    """
    Create a mapped_column for a gene_id foreign key.

    Args:
        nullable (bool): Whether the column is nullable. Defaults to False.
        index (bool): Whether to add an index. Defaults to True.

    Returns:
        Mapped[int]: SQLAlchemy mapped_column for gene_id foreign key to
            gene.gene_id.

    Example:
        gene_id: Mapped[int] = gene_id_column()
    """
    return mapped_column(
        Integer, ForeignKey("gene.gene_id"), nullable=nullable, index=index
    )


class GeneMetadataMixin:
    metadata = MetaData(schema="gene")


class GeneTableBase(DeclarativeTableBase, GeneMetadataMixin):
    stable_id = "source_id"


class GeneMaterializedViewBase(DeclarativeMaterializedViewBase, GeneMetadataMixin):
    document_primary_key = "gene_id"
    stable_id = "ensembl_id"
