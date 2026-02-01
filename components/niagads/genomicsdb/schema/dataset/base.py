"""
Base class for the `Dataset` schema models in the genomicsdb database.
"""

from niagads.genomicsdb.schema.mixins import GenomicsDBTableMixin
from niagads.genomicsdb.schema.registry import SchemaRegistry
from sqlalchemy import MetaData
from sqlalchemy.orm import DeclarativeBase


@SchemaRegistry.register()
class DatasetSchemaBase(DeclarativeBase):
    metadata = MetaData(schema="dataset")


class DatasetTableBase(DatasetSchemaBase, GenomicsDBTableMixin):
    __abstract__ = True
