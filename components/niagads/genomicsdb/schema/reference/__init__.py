from niagads.genomicsdb.schema.reference.base import ReferenceTableBase
from niagads.genomicsdb.schema.reference.interval_bin import IntervalBin
from niagads.genomicsdb.schema.reference.mixins import (
    ExternalDatabaseMixin,
    OntologyTermMixin,
)

__all__ = [
    "IntervalBin",
    "ExternalDatabaseMixin",
    "OntologyTermMixin",
]
