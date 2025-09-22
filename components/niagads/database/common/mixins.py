from datetime import datetime

from niagads.assembly.core import Human
from niagads.common.models.structures import Range
from niagads.database.common.decorators import RangeType
from niagads.database.common.utils import enum_column, enum_constraint
from sqlalchemy import DATETIME, Column, Index, UniqueConstraint, func
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.sql.schema import ForeignKey
from sqlalchemy_utils import LtreeType


class HousekeepingMixin(object):
    """
    Mixin providing common housekeeping fields for database models:
    - etl_log_id: Foreign key to Core.ETLLog table
    - modification_date: Timestamp of last modification
    - is_private: Boolean flag for privacy
    """

    etl_log_id: Mapped[int] = mapped_column(
        ForeignKey("core.etllog.etl_log_id"), nullable=False, index=True
    )
    modification_date: Mapped[datetime] = mapped_column(
        DATETIME,
        server_default=func.now(),
        nullable=False,
    )
    # is_private: Mapped[bool] = mapped_column(nullable=True, index=True)


class ExternalDBMixin(object):
    """
    Mixin providing fields and a unique constraint for linking to an external database and source identifier.

    Fields:
        external_database_id (int): Foreign key to core.externaldatabase.external_database_id.
        source_id (str): Source identifier within the external database.

    Constraints:
        - Unique constraint on (external_database_id, source_id) to ensure each source_id is unique within its external database.
    """

    external_database_id: Mapped[int] = mapped_column(
        ForeignKey("core.externaldatabase.external_database_id"),
        nullable=False,
        index=True,
    )
    source_id: Mapped[str] = mapped_column(index=True, nullable=False)

    __table_args__ = (
        UniqueConstraint(
            "external_database_id", "source_id", name="uq_externaldb_source"
        ),
    )


class TypeMixin(object):
    ontology_term_id: Mapped[int] = mapped_column()


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


class ModelDumpMixin(object):
    """
    Mixin providing a method to dump model column-value pairs as a dictionary.
    Mirrors pydantic model_dump
    """

    def model_dump(self):
        """Return a dictionary of column names and their values for the model instance."""
        return {
            column.name: getattr(self, column.name) for column in self.__table__.columns
        }
