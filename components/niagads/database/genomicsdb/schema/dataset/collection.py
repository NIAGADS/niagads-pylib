"""core defines the `Collection` and link between tracks and collections (metadata) database models"""

from typing import Optional

from niagads.database.genomicsdb.schema.dataset.base import DatasetTableBase
from niagads.database.genomicsdb.schema.dataset.helpers import track_fk_column
from niagads.database.genomicsdb.schema.mixins import IdAliasMixin
from niagads.database.genomicsdb.schema.reference.mixins import ExternalDatabaseMixin
from sqlalchemy import Column, ForeignKey, Index, String
from sqlalchemy.orm import Mapped, mapped_column


# this just adds housekeeping, etc to these schemas
class Collection(DatasetTableBase, IdAliasMixin, ExternalDatabaseMixin):
    _stable_id = "collection_key"
    __tablename__ = "collection"
    __table_args__ = (
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
        Index(
            "ix_metadata_collection_is_filer_collection_true",
            "is_filer_collection",
            postgresql_where=(Column("is_filer_track") == True),
        ),
        DatasetTableBase.__table_args__,
    )

    collection_id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    collection_key: Mapped[str]
    name: Mapped[str]
    description: Mapped[str] = mapped_column(String(2000))
    tracks_are_sharded: Mapped[Optional[bool]] = mapped_column(default=False)
    is_filer_collection: Mapped[bool] = mapped_column(default=False)


class TrackCollectionLink(DatasetTableBase):
    _stable_id = None
    __tablename__ = "trackcollectionlink"
    __table_args__ = (
        Index(
            "ix_metadata_trackcollectionlink_collection_id",
            "collection_id",
            postgresql_include=["track_id"],
        ),
        DatasetTableBase.__table_args__,
    )
    track_collection_link: Mapped[int] = mapped_column(
        primary_key=True, autoincrement=True
    )
    track_id: Mapped[int] = track_fk_column()
    collection_id: Mapped[int] = mapped_column(
        ForeignKey("dataset.collection.collection_id"), nullable=False, index=True
    )
