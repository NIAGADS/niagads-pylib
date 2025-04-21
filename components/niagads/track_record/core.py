"""core defines the `Track` (metadata) record database model"""

from typing import Optional

from niagads.genome.core import Assembly
from niagads.list_utils.core import list_to_string
from niagads.open_access_api_configuration.core import DataStore
from niagads.track_record.models.properties import (
    BiosampleCharacteristics,
    ExperimentalDesign,
    FileProperties,
    Provenance,
)
from sqlalchemy import TEXT, Column, Enum, MetaData, String
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column
from sqlalchemy.schema import CheckConstraint


class TrackBase(DeclarativeBase):
    """base class for the track database models"""

    metadata = MetaData(schema="track")


class Track(TrackBase):
    __tablename__ = "metadataentry"
    __table_args__ = (
        CheckConstraint(
            f"genome_build in ({list_to_string(Assembly.list(), quote=True, delim=', ')})",
            name="check_genome_build",
        ),
        CheckConstraint(
            f"data_store in ({list_to_string(DataStore.list(), quote=True, delim=', ')})",
            name="check_data_store",
        ),
    )

    metadata_entry_id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)

    track_id: Mapped[str] = mapped_column(unique=True, index=True)
    data_store: str = Column(
        Enum(DataStore, native_enum=False), nullable=False, index=True
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

    biosample_characteristics: Mapped[BiosampleCharacteristics] = mapped_column(JSONB)
    experimental_design: Mapped[ExperimentalDesign] = mapped_column(JSONB)
    provenance: Mapped[Provenance] = mapped_column(JSONB)
    properties: Mapped[FileProperties] = mapped_column(JSONB)
