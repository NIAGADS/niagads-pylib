"""
Base class for the `Core` schema models in the genomicsdb database.
Uses DeclarativeModelBaseFactory to create a SQLAlchemy DeclarativeBase with housekeeping fields.
"""

from niagads.genomicsdb.schema.bases import DeclarativeTableBase
from niagads.genomicsdb.schema.registry import SchemaRegistry
from sqlalchemy import MetaData


@SchemaRegistry.register()
class AdminSchema(DeclarativeTableBase):
    metadata = MetaData(schema="admin")
