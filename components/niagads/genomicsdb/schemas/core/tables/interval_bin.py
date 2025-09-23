"""`IntervalBin` database model"""

from niagads.database.mixins import GenomicRegionMixin
from niagads.database.genomicsdb.schemas.core.base import CoreSchemaBase
from sqlalchemy import String
from sqlalchemy.orm import Mapped, mapped_column


class IntervalBin(CoreSchemaBase, GenomicRegionMixin):
    __tablename__ = "etllog"

    interval_bin_id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    path: Mapped[str] = mapped_column(String(350))
