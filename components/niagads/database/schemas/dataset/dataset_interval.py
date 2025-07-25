from typing import Any, List
from niagads.database.core import ModelDumpMixin
from niagads.database.schemas.dataset.base import DatasetSchemaBase
from sqlalchemy import Index
from sqlalchemy.dialects.postgresql import INT8RANGE
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy_utils import LtreeType


class TrackInterval(ModelDumpMixin, DatasetSchemaBase):
    __tablename__ = "trackinterval"
    __table_args__ = (
        Index(
            "ix_index_trackinterval_track_id",
            "track_id",
            postgresql_include=["num_hits", "span"],
        ),
        Index("ix_index_trackinterval_bin_index", "bin_index", postgresql_using="gist"),
        Index(
            "ix_index_trackinterval_span", "track_id", "span", postgresql_using="gist"
        ),
    )

    track_interval_id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    bin_index: Mapped[str] = mapped_column(LtreeType)
    track_id: Mapped[str]  # TODO: mapped_column(ForeignKey("metadata.track.track_id"))
    num_hits: Mapped[int]
    span: Mapped[Any] = mapped_column(INT8RANGE)
