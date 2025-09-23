from niagads.assembly.core import Human
from niagads.common.models.structures import Range
from niagads.database import RangeType, enum_column, enum_constraint
from sqlalchemy import Index
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy_utils import LtreeType


class GenomicRegionMixin(object):
    """
    Mixin providing fields and indexes for a genomic region interval and its binning path.

    Fields:
        genomic_region (Range): Genomic interval (start/end) stored as a INT4RANGE object using RangeType.
        genomic_region_bin (str): Binning path for the region, stored as an ltree string.

    Indexes:
        - GiST index on genomic_region for efficient range queries.
        - GiST index on genomic_region_bin for LTree queries.
    """

    # native_enum set to True here, so postgres will sort the columns by the enum
    # ordering; may potentially throw a "type already exists error" during migration
    chromosome: str = enum_column(Human, native_enum=True)
    genomic_region: Mapped[Range] = mapped_column(RangeType, nullable=False)
    genomic_region_bin: Mapped[str] = mapped_column(LtreeType)

    __table_args__ = (
        enum_constraint("chromosome", Human),
        Index("ix_genomic_region_gist", "genomic_region", postgresql_using="gist"),
        Index(
            "ix_genomic_region_bin_gist", "genomic_region_bin", postgresql_using="gist"
        ),
    )
