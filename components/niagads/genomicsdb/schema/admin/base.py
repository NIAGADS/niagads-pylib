"""
Base class for the `Admin` schema models in the genomicsdb database.
"""

from niagads.database.mixins.serialization import ModelDumpMixin
from niagads.database.mixins.transactions import TransactionTableMixin
from niagads.genomicsdb.schema.base import GenomicsDBSchemaBase
from niagads.genomicsdb.schema.mixins import LookupTableMixin


# don't need housekeeping fields for Admin Tables
class AdminTableBase(
    GenomicsDBSchemaBase, ModelDumpMixin, LookupTableMixin, TransactionTableMixin
):
    _schema = "admin"
    __abstract__ = True
    __table_args__ = {"schema": _schema}
