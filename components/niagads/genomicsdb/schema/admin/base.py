"""
Base class for the `Admin` schema models in the genomicsdb database.
"""

from niagads.genomicsdb.schema.mixins import GenomicsDBTableMixin
from niagads.genomicsdb.schema.registry import SchemaRegistry
from sqlalchemy import MetaData
from sqlalchemy.orm import DeclarativeBase


@SchemaRegistry.register()
class AdminSchemaBase(DeclarativeBase):
    metadata = MetaData(schema="admin")


class AdminTableBase(AdminSchemaBase, GenomicsDBTableMixin):
    __abstract__ = True
