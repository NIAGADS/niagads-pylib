"""
Base class for the `Core` schema models in the genomicsdb database.
Uses DeclarativeModelBaseFactory to create a SQLAlchemy DeclarativeBase with housekeeping fields.
"""

from niagads.genomicsdb.schema.base import DeclarativeTableBase
from sqlalchemy import MetaData
from sqlalchemy.orm import DeclarativeBase

SCHEMA = "admin"


class AdminSchemaBase(DeclarativeBase):
    metadata = MetaData(schema=SCHEMA)


class AdminTableBase(DeclarativeTableBase):
    __abstract__ = True
    metadata = MetaData(schema=SCHEMA)
