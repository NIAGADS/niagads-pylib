"""`Track` (metadata) database model"""

from typing import List, Optional

from niagads.common.track.models import (
    BiosampleCharacteristics,
    ExperimentalDesign,
    FileProperties,
    Phenotype,
    Provenance,
)
from niagads.common.track.models.curation import CurationEvent
from niagads.common.track.models.phenotypes import PhenotypeCount
from niagads.database.helpers import enum_column, enum_constraint
from niagads.database.mixins import GenomicRegionMixin
from niagads.genome_reference.human import GenomeBuild, HumanGenome
from niagads.database.genomicsdb.schema.dataset.base import DatasetTableBase
from niagads.database.genomicsdb.schema.dataset.helpers import track_fk_column
from niagads.database.genomicsdb.schema.mixins import IdAliasMixin
from niagads.database.genomicsdb.schema.reference.helpers import ontology_term_fk_column
from niagads.database.genomicsdb.schema.reference.mixins import ExternalDatabaseMixin
from sqlalchemy import TEXT, Column, ForeignKey, Index, Integer, String
from sqlalchemy.dialects.postgresql import JSONB, ARRAY
from sqlalchemy.orm import Mapped, mapped_column


class Track(DatasetTableBase, ExternalDatabaseMixin, IdAliasMixin):
    _stable_id = "source_id"
    __tablename__ = "track"
    __table_args__ = (
        *ExternalDatabaseMixin.__table_args__,
        enum_constraint("genome_build", GenomeBuild),
        enum_constraint("shard_chromosome", HumanGenome),
        Index(
            "ix_dataset_track_is_filer_track_true",
            "is_filer_track",
            postgresql_where=(Column("is_filer_track") == True),
        ),
        DatasetTableBase.__table_args__,
    )

    track_id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)

    is_filer_track: Mapped[bool] = mapped_column()

    # FIXME: when we revisit ontology terms
    dataset_type_id: Mapped[int] = ontology_term_fk_column()

    name: Mapped[str]
    description: Mapped[str] = mapped_column(String(2000))

    genome_build: Mapped[str] = enum_column(GenomeBuild)

    feature_type: Mapped[str] = mapped_column(String(50), index=True)
    is_download_only: Mapped[bool] = mapped_column(index=True)

    is_shard: Mapped[Optional[bool]]
    shard_chromosome: Mapped[str] = enum_column(
        HumanGenome, index=False, nullable=True, native_enum=True, use_enum_names=True
    )

    cohorts: Mapped[Optional[List[str]]] = mapped_column(ARRAY(String))

    biosample_characteristics: Mapped[Optional[BiosampleCharacteristics]] = (
        mapped_column(JSONB(none_as_null=True))
    )
    participant_phenotypes: Mapped[Optional[Phenotype]] = mapped_column(
        JSONB(none_as_null=True)
    )
    experimental_design: Mapped[Optional[ExperimentalDesign]] = mapped_column(
        JSONB(none_as_null=True)
    )
    provenance: Mapped[Provenance] = mapped_column(JSONB(none_as_null=True))
    file_properties: Mapped[Optional[FileProperties]] = mapped_column(
        JSONB(none_as_null=True)
    )
    study_diagnosis: Mapped[Optional[List[PhenotypeCount]]] = mapped_column(
        JSONB(none_as_null=True)
    )
    curation_history: Mapped[Optional[List[CurationEvent]]] = mapped_column(
        JSONB(none_as_null=True)
    )


class TrackInterval(DatasetTableBase, GenomicRegionMixin):
    """indexing table; stores the number of hits per bin index for a track"""

    _stable_id = None
    __tablename__ = "trackinterval"
    __table_args__ = (
        *GenomicRegionMixin.__table_args__,  # Unpack mixin's args first
        *GenomicRegionMixin.get_indexes(DatasetTableBase._schema, __tablename__),
        *GenomicRegionMixin.set_bin_index_fk(DatasetTableBase._schema, __tablename__),
        Index(
            "ix_index_trackinterval_track_id",
            "track_id",
            postgresql_include=["num_hits", "span"],
        ),
        DatasetTableBase.__table_args__,
    )

    track_interval_id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    track_id: Mapped[int] = track_fk_column()
    num_hits: Mapped[int] = mapped_column(Integer, nullable=False)
