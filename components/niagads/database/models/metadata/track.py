"""`Track` (metadata) database model"""

from typing import List, Optional

from niagads.database.models.metadata.composite_attributes import (
    BiosampleCharacteristics,
    ExperimentalDesign,
    FileProperties,
    Phenotype,
    Provenance,
    TrackDataStore,
)
from niagads.database.models.metadata.base import MetadataSchemaBase
from niagads.genome.core import Assembly, Human
from niagads.utils.list import list_to_string
from sqlalchemy import ARRAY, TEXT, Column, Enum, Index, String
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
        CheckConstraint(
            f"shard_chromosome in ({list_to_string(Human.list(), quote=True, delim=', ')})",
            name="check_shard_chromosome",
        ),
        Index(
            "ix_metadata_track_shard_root_track_id",
            "shard_root_track_id",
            postgresql_where=(Column("shard_root_track_id").isnot(None)),
        ),
        Index(
            "ix_metadata_track_searchable_text",
            "searchable_text",
            postgresql_using="gin",
            postgresql_ops={
                "searchable_text": "gin_trgm_ops",
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

    searchable_text: Mapped[str] = mapped_column(TEXT)

    is_shard: Mapped[Optional[bool]]
    shard_chromosome: str = Column(Enum(Human, native_enum=False))
    shard_root_track_id: Mapped[Optional[str]] = mapped_column()

    cohorts: Mapped[List[str]] = mapped_column(ARRAY(String))

    biosample_characteristics: Mapped[Optional[BiosampleCharacteristics]] = (
        mapped_column(JSONB)
    )
    subject_phenotypes: Mapped[Optional[Phenotype]] = mapped_column(JSONB)
    experimental_design: Mapped[Optional[ExperimentalDesign]] = mapped_column(JSONB)
    provenance: Mapped[Provenance] = mapped_column(JSONB)

    file_properties: Mapped[Optional[FileProperties]] = mapped_column(JSONB)
