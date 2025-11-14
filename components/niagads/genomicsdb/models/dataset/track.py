"""`Track` (metadata) database model"""

from niagads.database.mixins import GenomicRegionMixin, TrackMixin
from niagads.genomicsdb.models.dataset.base import DatasetSchemaBase
from niagads.genomicsdb.models.reference.mixins import (
    ExternalDBMixin,
    OntologyTermMixin,
)
from sqlalchemy import Index
from sqlalchemy.orm import Mapped, mapped_column


class Track(OntologyTermMixin, TrackMixin, ExternalDBMixin, DatasetSchemaBase): ...


class TrackInterval(GenomicRegionMixin, DatasetSchemaBase):
    """indexing table; stores the number of hits per bin index for a track"""

    __tablename__ = "trackinterval"
    __table_args__ = (
        Index(
            "ix_index_trackinterval_track_id",
            "track_id",
            postgresql_include=["num_hits", "span"],
        ),
    )

    track_interval_id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    track_id: Mapped[str]  # TODO: mapped_column(ForeignKey("metadata.track.track_id"))
    num_hits: Mapped[int]
