"""`Track` (metadata) database model"""

from typing import List, Optional

from niagads.common.constants.track import TrackDataStore
from niagads.common.models.metadata import (
    BiosampleCharacteristics,
    ExperimentalDesign,
    FileProperties,
    Phenotype,
    Provenance,
)
from niagads.database.helpers import enum_column, enum_constraint
from niagads.database.mixins import GenomicRegionMixin
from niagads.genomics.sequence.assembly import Assembly, HumanGenome
from niagads.genomicsdb.schema.dataset.base import DatasetTableBase
from niagads.genomicsdb.schema.dataset.helpers import track_fk_column
from niagads.genomicsdb.schema.mixins import IdAliasMixin
from niagads.genomicsdb.schema.reference.helpers import ontology_term_fk_column
from niagads.genomicsdb.schema.reference.mixins import ExternalDatabaseMixin
from sqlalchemy import ARRAY, TEXT, Column, Index, Integer, String
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column


class Track(DatasetTableBase, ExternalDatabaseMixin, IdAliasMixin):
    _stable_id = "source_id"
    __tablename__ = "track"
    __table_args__ = (
        *ExternalDatabaseMixin.__table_args__,
        enum_constraint("genome_build", Assembly),
        enum_constraint("data_store", TrackDataStore),
        enum_constraint("shard_chromosome", HumanGenome),
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
        DatasetTableBase.__table_args__,
    )

    track_id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)

    data_store: Mapped[str] = enum_column(TrackDataStore)
    dataset_type_id: Mapped[int] = ontology_term_fk_column()

    name: Mapped[str]
    description: Mapped[str] = mapped_column(String(2000))

    genome_build: Mapped[str] = enum_column(Assembly)

    feature_type: Mapped[str] = mapped_column(String(50), index=True)
    is_download_only: Mapped[bool] = mapped_column(default=False, index=True)

    searchable_text: Mapped[str] = mapped_column(TEXT)

    is_shard: Mapped[Optional[bool]]
    shard_chromosome: Mapped[str] = enum_column(
        HumanGenome, index=False, nullable=True, native_enum=True
    )
    shard_root_track_id: Mapped[Optional[str]] = mapped_column()

    cohorts: Mapped[Optional[List[str]]] = mapped_column(ARRAY(String))

    biosample_characteristics: Mapped[Optional[BiosampleCharacteristics]] = (
        mapped_column(JSONB(none_as_null=True))
    )
    subject_phenotypes: Mapped[Optional[Phenotype]] = mapped_column(
        JSONB(none_as_null=True)
    )
    experimental_design: Mapped[Optional[ExperimentalDesign]] = mapped_column(
        JSONB(none_as_null=True)
    )
    provenance: Mapped[Provenance] = mapped_column(JSONB(none_as_null=True))
    file_properties: Mapped[Optional[FileProperties]] = mapped_column(
        JSONB(none_as_null=True)
    )


class TrackInterval(DatasetTableBase, GenomicRegionMixin):
    """indexing table; stores the number of hits per bin index for a track"""

    _stable_id = None
    __tablename__ = "trackinterval"
    __table_args__ = (
        *GenomicRegionMixin.__table_args__,  # Unpack mixin's args first
        *GenomicRegionMixin.get_indexes(DatasetTableBase._schema, __tablename__),
        Index(
            "ix_index_trackinterval_track_id",
            "track_id",
            postgresql_include=["num_hits", "genomic_region"],
        ),
        DatasetTableBase.__table_args__,
    )

    track_interval_id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    track_id: Mapped[int] = track_fk_column()
    num_hits: Mapped[int] = mapped_column(Integer, nullable=False)
