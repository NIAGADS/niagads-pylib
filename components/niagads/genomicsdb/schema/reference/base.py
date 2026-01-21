"""
Base class for the `Core` schema models in the genomicsdb database.
Uses DeclarativeModelBaseFactory to create a SQLAlchemy DeclarativeBase with housekeeping fields.
"""

from niagads.genomicsdb.schema.base import DeclarativeTableBase
from sqlalchemy import MetaData


class ReferenceSchemaBase(DeclarativeTableBase):
    metadata = MetaData(schema="reference")
    stable_id = None
