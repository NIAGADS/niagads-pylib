from niagads.database.helpers import enum_column, enum_constraint
from niagads.genome_reference.human import HumanGenome
from niagads.common.models.types import Range
from niagads.database import RangeType
from sqlalchemy import Index, ForeignKeyConstraint
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
    chromosome: Mapped[str] = enum_column(
        HumanGenome, native_enum=True, use_enum_names=True
    )
    genomic_region: Mapped[Range] = mapped_column(RangeType, nullable=False)
    bin_index: Mapped[str] = mapped_column(LtreeType)

    __table_args__ = (enum_constraint("chromosome", HumanGenome, use_enum_names=True),)

    @classmethod
    def get_indexes(cls, schema: str, table: str):
        """Return only the Index objects from __table_args__"""

        prefix = f"ix_{schema}_{table}_"
        return (
            Index(f"{prefix}_{field}", field, postgresql_using="gist")
            for field in ["bin_index", "genomic_region"]
        )

    @classmethod
    def set_bin_index_fk(
        cls, schema: str, table: str, column_name: str = "bin_index"
    ) -> ForeignKeyConstraint:
        """
        Create a foreign key constraint to reference.bin_interval.bin_index.

        Can be used in __table_args__ to define a foreign key to the bin_interval table.
        Generates a unique constraint name based on schema and table to avoid collisions.

        Args:
            schema: Schema name (e.g., 'gene', 'dataset')
            table: Table name (e.g., 'gene', 'exon')
            column_name: Name of the column to reference the bin_index (default: 'bin_index')

        Returns:
            ForeignKeyConstraint for use in __table_args__
        """
        constraint_name = f"fk_{schema}_{table}_{column_name}"
        return ForeignKeyConstraint(
            [column_name],
            ["reference.bin_interval.bin_index"],
            name=constraint_name,
        )
