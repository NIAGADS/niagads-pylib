"""
Base classes for SQLAlchemy ORM models in the GenomicsDB "Reference" schema.
"""

from niagads.genomicsdb.schema.base import GenomicsDBSchemaBase
from niagads.genomicsdb.schema.mixins import GenomicsDBTableMixin
from sqlalchemy import MetaData
from sqlalchemy.orm import DeclarativeBase


class ReferenceTableBase(GenomicsDBSchemaBase, GenomicsDBTableMixin):
    __abstract__ = True
    _stable_id = None
    _schema = "reference"

    __table_args__ = {"schema": _schema}
