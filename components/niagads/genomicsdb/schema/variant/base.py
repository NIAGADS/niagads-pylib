"""
Base classes for SQLAlchemy ORM models in the GenomicsDB "Gene" schema.
"""

from niagads.genomicsdb.schema.base import GenomicsDBSchemaBase
from niagads.genomicsdb.schema.mixins import GenomicsDBTableMixin


class VariantTableBase(GenomicsDBSchemaBase, GenomicsDBTableMixin):
    __abstract__ = True
    _stable_id = "positional_id"
    _schema = "variant"

    __table_args__ = {"schema": _schema}
