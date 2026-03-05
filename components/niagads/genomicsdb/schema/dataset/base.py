"""
Base class for the `Dataset` schema models in the genomicsdb database.
"""

from niagads.genomicsdb.schema.base import GenomicsDBSchemaBase
from niagads.genomicsdb.schema.mixins import GenomicsDBTableMixin


class DatasetTableBase(GenomicsDBSchemaBase, GenomicsDBTableMixin):
    _schema = "dataset"
    __abstract__ = True
    __table_args__ = {"schema": _schema}
