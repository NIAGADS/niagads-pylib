"""
Base classes and helpers for SQLAlchemy ORM models in the genomicsdb gene schema.

Defines declarative base classes, metadata mixins, and foreign key helpers for gene-related tables.
"""

from niagads.genomicsdb.schema.bases import (
    DeclarativeMaterializedViewBase,
    DeclarativeTableBase,
)
from sqlalchemy import MetaData


class GeneMetadataMixin:
    metadata = MetaData(schema="gene")


class GeneTableBase(DeclarativeTableBase, GeneMetadataMixin):
    stable_id = "source_id"


class GeneMaterializedViewBase(DeclarativeMaterializedViewBase, GeneMetadataMixin):
    document_primary_key = "gene_id"
    stable_id = "ensembl_id"
