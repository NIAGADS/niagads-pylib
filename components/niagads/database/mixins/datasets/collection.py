"""core defines the `Collection` and link between tracks and collections (metadata) database models"""

from typing import Optional

from niagads.database.sa_enum_utils import enum_constraint
from niagads.database.mixins.datasets.track import TrackDataStore
from sqlalchemy import Column, Enum, ForeignKey, Index, String
from sqlalchemy.orm import Mapped, mapped_column


class CollectionMixin:
    __tablename__ = "collection"
    __table_args__ = (
        enum_constraint("data_store", TrackDataStore),
        Index(
            "ix_metadata_collection_data_store",
            "data_store",
            postgresql_include=["name", "description", "tracks_are_sharded"],
        ),
        Index(
            "ix_metadata_collection_primary_key_unique",
            "primary_key",
            unique=True,
        ),
    )

    collection_id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    primary_key: Mapped[str]
    name: Mapped[str]
    description: Mapped[str] = mapped_column(String(2000))
    tracks_are_sharded: Mapped[Optional[bool]] = mapped_column(default=False)
    data_store: str = Column(Enum(TrackDataStore, native_enum=False), nullable=False)


class TrackCollectionMixin:
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
    track_id: Mapped[str] = mapped_column(
        ForeignKey("track.track_id"),
        index=True,
        nullable=False,
    )
    collection_id: Mapped[int] = mapped_column(
        ForeignKey("collection.collection_id"), nullable=False
    )
