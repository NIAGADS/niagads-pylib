"""
Base class for the `Dataset` schema models in the genomicsdb database.
"""

from niagads.database.genomicsdb.schema.base import GenomicsDBSchemaBase
from niagads.database.genomicsdb.schema.mixins import GenomicsDBTableMixin


class DatasetTableBase(GenomicsDBSchemaBase, GenomicsDBTableMixin):
    _schema = "dataset"
    __abstract__ = True
    __table_args__ = {"schema": _schema}
