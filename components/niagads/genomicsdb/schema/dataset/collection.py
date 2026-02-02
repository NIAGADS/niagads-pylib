"""core defines the `Collection` and link between tracks and collections (metadata) database models"""

from typing import Optional
from niagads.common.constants.track import TrackDataStore
from niagads.database.helpers import enum_column, enum_constraint
from niagads.genomicsdb.schema.dataset.base import DatasetTableBase
from niagads.genomicsdb.schema.dataset.helpers import track_fk_column
from niagads.genomicsdb.schema.mixins import IdAliasMixin
from sqlalchemy import ForeignKey, Index, String
from sqlalchemy.orm import Mapped, mapped_column


# this just adds housekeeping, etc to these schemas
class Collection(DatasetTableBase, IdAliasMixin):
    _stable_id = "collection_key"
    __tablename__ = "collection"
    __table_args__ = (
        enum_constraint("data_store", TrackDataStore),
        Index(
            "ix_metadata_collection_data_store",
            "data_store",
            postgresql_include=["name", "description", "tracks_are_sharded"],
        ),
        Index(
            "ix_metadata_collection_key_unique",
            "collection_key",
            unique=True,
        ),
    )

    collection_id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    collection_key: Mapped[str]
    name: Mapped[str]
    description: Mapped[str] = mapped_column(String(2000))
    tracks_are_sharded: Mapped[Optional[bool]] = mapped_column(default=False)
    data_store: Mapped[str] = enum_column(TrackDataStore)


class TrackCollectionLink(DatasetTableBase):
    _stable_id = None
    __tablename__ = "trackcollectionlink"
    __table_args__ = (
        Index(
            "ix_metadata_trackcollectionlink_collection_id",
            "collection_id",
            postgresql_include=["track_id"],
        ),
    )
    track_collection_link: Mapped[int] = mapped_column(
        primary_key=True, autoincrement=True
    )
    track_id: Mapped[int] = track_fk_column()
    collection_id: Mapped[int] = mapped_column(
        ForeignKey("dataset.collection.collection_id"), nullable=False, index=True
    )
