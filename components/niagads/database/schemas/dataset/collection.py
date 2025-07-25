"""core defines the `Collection` and link between tracks and collections (metadata) database models"""

from typing import Optional

from niagads.database.core import ModelDumpMixin
from niagads.database.schemas.dataset.base import DatasetSchemaBase
from niagads.database.schemas.dataset.track import TrackDataStore
from niagads.utils.list import list_to_string
from sqlalchemy import CheckConstraint, Column, Enum, ForeignKey, Index, String
from sqlalchemy.orm import Mapped, mapped_column


class Collection(ModelDumpMixin, DatasetSchemaBase):
    __tablename__ = "collection"
    __table_args__ = (
        CheckConstraint(
            f"data_store in ({list_to_string(TrackDataStore.list(), quote=True, delim=', ')})",
            name="check_data_store",
        ),
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


class TrackCollection(DatasetSchemaBase):
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
