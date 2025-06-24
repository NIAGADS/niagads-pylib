from typing import Any, List
from niagads.database.models.core import ModelDumpMixin
from niagads.database.models.index.base import IndexSchemaBase
from sqlalchemy import Index
from sqlalchemy.dialects.postgresql import INT8RANGE
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy_utils import LtreeType


class DatasetInterval(ModelDumpMixin, IndexSchemaBase):
    __tablename__ = "datasetinterval"
    __table_args__ = (
        Index(
            "ix_index_datasetinterval_track_id",
            "track_id",
            postgresql_include=["num_hits", "span"],
        ),
        Index(
            "ix_index_datasetinterval_bin_index", "bin_index", postgresql_using="gist"
        ),
        Index(
            "ix_index_datasetinterval_span", "track_id", "span", postgresql_using="gist"
        ),
    )

    dataset_interval_id: Mapped[int] = mapped_column(
        primary_key=True, autoincrement=True
    )
    bin_index: Mapped[str] = mapped_column(LtreeType)
    track_id: Mapped[str]  # TODO: mapped_column(ForeignKey("metadata.track.track_id"))
    num_hits: Mapped[int]
    span: Mapped[Any] = mapped_column(INT8RANGE)
