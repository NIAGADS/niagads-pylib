"""
Base class for the `Gene` schema models in the genomicsdb database.
Uses DeclarativeModelBaseFactory to create a SQLAlchemy DeclarativeBase with housekeeping fields.
"""

from niagads.genomicsdb.schema.base import (
    DeclarativeTableBase,
    DeclarativeMaterializedViewBase,
)
from sqlalchemy import MetaData


class GeneMetadataMixin:
    metadata = MetaData(schema="gene")
    stable_id = "ensembl_id"


class GeneSchemaBase(DeclarativeTableBase, GeneMetadataMixin): ...


class GeneMaterializedViewBase(DeclarativeMaterializedViewBase, GeneMetadataMixin): ...
