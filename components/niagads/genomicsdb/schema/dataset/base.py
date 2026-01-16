"""
Base class for the `Dataset` schema models in the genomicsdb database.
Uses DeclarativeModelBaseFactory to create a SQLAlchemy DeclarativeBase with housekeeping fields.
"""

from niagads.genomicsdb.schema.base import DeclarativeTableBase
from sqlalchemy import MetaData


class DatasetSchemaBase(DeclarativeTableBase):
    metadata = MetaData(schema="dataset")
