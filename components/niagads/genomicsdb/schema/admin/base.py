"""
Base class for the `Admin` schema models in the genomicsdb database.
"""

from niagads.database.mixins.serialization import ModelDumpMixin
from niagads.genomicsdb.schema.mixins import LookupTableMixin, TransactionTableMixin
from niagads.genomicsdb.schema.registry import SchemaRegistry
from sqlalchemy import MetaData
from sqlalchemy.orm import DeclarativeBase


@SchemaRegistry.register()
class AdminSchemaBase(DeclarativeBase):
    metadata = MetaData(schema="admin")


# don't need housekeeping fields for Admin Tables
class AdminTableBase(
    AdminSchemaBase, ModelDumpMixin, LookupTableMixin, TransactionTableMixin
):
    __abstract__ = True
