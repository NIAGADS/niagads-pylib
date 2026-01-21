"""
Base class for the `Core` schema models in the genomicsdb database.
Uses DeclarativeModelBaseFactory to create a SQLAlchemy DeclarativeBase with housekeeping fields.
"""

from niagads.genomicsdb.schema.bases import DeclarativeTableBase
from sqlalchemy import MetaData


class ReferenceSchemaBase(DeclarativeBase):
    metadata = MetaData(schema="reference")


class ReferenceTableBase(ReferenceSchemaBase, DeclarativeTableBase):

    stable_id = None
