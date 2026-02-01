"""`IntervalBin` database model"""

from niagads.database import GenomicRegionMixin
from niagads.genomicsdb.schema.reference.base import ReferenceTableBase
from sqlalchemy import String
from sqlalchemy.orm import Mapped, mapped_column


class IntervalBin(ReferenceTableBase, GenomicRegionMixin):
    __tablename__ = "intervalbin"
    _stable_id = "bin_index"

    interval_bin_id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    path: Mapped[str] = mapped_column(String(350))
