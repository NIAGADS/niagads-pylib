"""
Base class for the `Gene` schema models in the genomicsdb database.
Uses DeclarativeModelBaseFactory to create a SQLAlchemy DeclarativeBase with housekeeping fields.
"""

from niagads.genomicsdb.schema.base import (
    DeclarativeTableBase,
    DeclarativeMaterializedViewBase,
)
from sqlalchemy import MetaData


class GeneSchemaBase(DeclarativeTableBase):
    metadata = MetaData(schema="gene")


class GeneMaterializedViewBase(DeclarativeMaterializedViewBase):
    metadata = MetaData(schema="gene")
