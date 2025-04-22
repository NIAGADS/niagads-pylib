"""`Track` (metadata) database model"""

from typing import Optional

from niagads.database.models.metadata.composite_attributes import (
    BiosampleCharacteristics,
    ExperimentalDesign,
    FileProperties,
    Phenotype,
    Provenance,
    TrackDataStore,
)
from niagads.database.models.metadata.core import MetadataSchemaBase
from niagads.genome.core import Assembly
from niagads.utils.list import list_to_string
from sqlalchemy import TEXT, Column, Enum, Index, String
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.schema import CheckConstraint


class Track(MetadataSchemaBase):
    __tablename__ = "track"
    __table_args__ = (
        CheckConstraint(
            f"genome_build in ({list_to_string(Assembly.list(), quote=True, delim=', ')})",
            name="check_genome_build",
        ),
        CheckConstraint(
            f"data_store in ({list_to_string(TrackDataStore.list(), quote=True, delim=', ')})",
            name="check_data_store",
        ),
        Index("idx_track_track_id", "track_id", unique=True),
        Index("idx_track_data_store", "data_store"),
        Index("idx_track_genome_build", "genome_build"),
        Index("idx_track_feature_type", "feature_type"),
        Index("idx_track_is_download_only", "is_download_only"),
        Index(
            "idx_track_shard_root_track_id",
            "shard_root_track_id",
            postgresql_where=(Column("shard_root_track_id").isnot(None)),
        ),
        Index(
            "idx_track_searchable_text",
            "searchable_text",
            postgresql_using="gin",
            postgresql_ops={
                "name": "gin_trgm_ops",
            },
        ),
    )

    track_metadata_entry_id: Mapped[int] = mapped_column(
        primary_key=True, autoincrement=True
    )

    track_id: Mapped[str] = mapped_column(unique=True, index=True)
    data_store: str = Column(
        Enum(TrackDataStore, native_enum=False), nullable=False, index=True
    )
    name: Mapped[str]
    description: Mapped[str] = mapped_column(String(2000))

    genome_build: str = Column(
        Enum(Assembly, native_enum=False), nullable=False, index=True
    )

    feature_type: Mapped[str] = mapped_column(String(50), index=True)
    is_download_only: Mapped[bool] = mapped_column(default=False, index=True)

    searchable_text: Mapped[str] = mapped_column(TEXT, index=True)

    is_shard: Mapped[Optional[bool]]
    shard_root_track_id: Mapped[Optional[str]] = mapped_column(index=True)

    biosample_characteristics: Mapped[Optional[BiosampleCharacteristics]] = (
        mapped_column(JSONB)
    )
    phenotypes: Mapped[Optional[Phenotype]] = mapped_column(JSONB)
    experimental_design: Mapped[Optional[ExperimentalDesign]] = mapped_column(JSONB)
    provenance: Mapped[Provenance] = mapped_column(JSONB)

    file_properties: Mapped[Optional[FileProperties]] = mapped_column(JSONB)
