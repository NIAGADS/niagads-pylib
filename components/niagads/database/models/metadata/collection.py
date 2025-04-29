"""core defines the `Collection` and link between tracks and collections (metadata) database models"""

from typing import Optional
from niagads.database.models.metadata.composite_attributes import TrackDataStore
from niagads.database.models.metadata.core import MetadataSchemaBase
from niagads.utils.list import list_to_string
from sqlalchemy import CheckConstraint, Column, Enum, ForeignKey, Index, String
from sqlalchemy.orm import Mapped, mapped_column


class Collection(MetadataSchemaBase):
    __tablename__ = "collection"
    __table_args__ = (
        CheckConstraint(
            f"data_store in ({list_to_string(TrackDataStore.list(), quote=True, delim=', ')})",
            name="check_data_store",
        ),
        Index(
            "idx_collection_data_store",
            "data_store",
            postgresql_include=["name", "description", "tracks_are_sharded"],
        ),
    )

    collection_id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    name: Mapped[str]
    description: Mapped[str] = mapped_column(String(2000))
    tracks_are_sharded: Mapped[Optional[bool]] = mapped_column(default=False)
    data_store: str = Column(
        Enum(TrackDataStore, native_enum=False), nullable=False, index=True
    )


class TrackCollection(MetadataSchemaBase):
    __tablename__ = "trackcollectionlink"
    __table_args__ = (
        Index(
            "idx_tclink_collection_id", "collection_id", postgresql_include=["track_id"]
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
        ForeignKey("collection.collection_id"), index=True, nullable=False
    )
