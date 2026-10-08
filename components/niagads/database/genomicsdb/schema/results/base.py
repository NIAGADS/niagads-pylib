"""
Base class for the `Dataset` schema models in the genomicsdb database.
"""

from niagads.database.genomicsdb.schema.base import GenomicsDBSchemaBase
from niagads.database.genomicsdb.schema.mixins import GenomicsDBTableMixin


class ResultsTableBase(GenomicsDBSchemaBase, GenomicsDBTableMixin):
    _schema = "results"
    _stable_id: str = None
    __abstract__ = True
    __table_args__ = {"schema": _schema}
