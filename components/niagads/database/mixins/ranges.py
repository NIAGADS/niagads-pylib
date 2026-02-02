from niagads.database.helpers import enum_column, enum_constraint
from niagads.genomics.sequence.assembly import HumanGenome
from niagads.common.models.structures import Range
from niagads.database import RangeType
from sqlalchemy import Index
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy_utils import LtreeType


class GenomicRegionMixin(object):
    """
    Mixin providing fields and indexes for a genomic region interval and its binning path.

    Fields:
        genomic_region (Range): Genomic interval (start/end) stored as a INT4RANGE object using RangeType.
        bin_index (str): Binning path for the region, stored as an ltree string.

    Indexes:
        - GiST index on genomic_region for efficient range queries.
        - GiST index on bin_index for LTree queries.
    """

    # native_enum set to True here, so postgres will sort the columns by the enum
    # ordering; may potentially throw a "type already exists error" during migration
    chromosome: Mapped[str] = enum_column(HumanGenome, native_enum=True)
    genomic_region: Mapped[Range] = mapped_column(RangeType, nullable=False)
    bin_index: Mapped[str] = mapped_column(LtreeType)

    __table_args__ = (
        enum_constraint("chromosome", HumanGenome),
        Index(None, "genomic_region", postgresql_using="gist"),
        Index(None, "bin_index", postgresql_using="gist"),
    )
