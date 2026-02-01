"""
Base classes for SQLAlchemy ORM models in the GenomicsDB "Gene" schema.
"""

from niagads.genomicsdb.schema.mixins import GenomicsDBTableMixin
from niagads.genomicsdb.schema.registry import SchemaRegistry
from sqlalchemy import MetaData
from sqlalchemy.orm import DeclarativeBase


@SchemaRegistry.register()
class VariantSchemaBase(DeclarativeBase):
    metadata = MetaData(schema="dataset")


class VariantTableBase(VariantSchemaBase, GenomicsDBTableMixin):
    __abstract__ = True
    _stable_id = "positional_id"
