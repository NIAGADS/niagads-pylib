"""`Track` (metadata) database model"""

from enum import auto
from typing import List, Optional, Union

from niagads.common.nlp.embedding.types import Embedding, EmbeddingFunction
from niagads.common.search.models.record import SearchMatch
from niagads.common.search.types import MatchType
from niagads.common.track.models import (
    BiosampleCharacteristics,
    CurationEvent,
    ExperimentalDesign,
    FileProperties,
    Phenotype,
    Provenance,
)
from niagads.common.track.models.phenotypes import PhenotypeCount
from niagads.common.types import Entity, RecordRetrievalResult
from niagads.database.genomicsdb.schema.admin.catalog import TableCatalog
from niagads.database.genomicsdb.schema.dataset.base import DatasetTableBase
from niagads.database.genomicsdb.schema.dataset.helpers import track_fk_column
from niagads.database.genomicsdb.schema.mixins import (
    BulkRecordRetrievalMixin,
    IdAliasMixin,
    SearchMixin,
)
from niagads.database.genomicsdb.schema.ragdoc.chunks import (
    ChunkEmbedding,
    ChunkMetadata,
)
from niagads.database.genomicsdb.schema.reference.helpers import ontology_term_fk_column
from niagads.database.genomicsdb.schema.reference.mixins import ExternalDatabaseMixin
from niagads.database.genomicsdb.schema.reference.ontology import OntologyTerm
from niagads.database.helpers import enum_column, enum_constraint
from niagads.database.mixins import GenomicRegionMixin
from niagads.enums.core import CaseInsensitiveEnum
from niagads.genome_reference.human import GenomeBuild, HumanGenome
from sqlalchemy import (
    Column,
    Index,
    Integer,
    String,
    func,
    literal,
    select,
    true,
    union_all,
)
from sqlalchemy.dialects.postgresql import ARRAY, JSONB
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import Mapped, mapped_column


class Track(
    DatasetTableBase,
    ExternalDatabaseMixin,
    IdAliasMixin,
    SearchMixin,
    BulkRecordRetrievalMixin,
):
    _stable_id = "source_id"
    __tablename__ = "track"
    __table_args__ = (
        *ExternalDatabaseMixin.__table_args__,
        enum_constraint("genome_build", GenomeBuild),
        enum_constraint("shard_chromosome", HumanGenome),
        Index(
            "ix_dataset_track_name_trgm",
            "name",
            postgresql_using="gin",
            postgresql_ops={"name": "gin_trgm_ops"},
        ),
        Index(
            "ix_dataset_track_description_trgm",
            "description",
            postgresql_using="gin",
            postgresql_ops={"description": "gin_trgm_ops"},
        ),
        Index("ix_dataset_track_source_id_upper", func.upper(Column("source_id"))),
        Index(
            "ix_dataset_track_is_filer_track_true",
            "is_filer_track",
            postgresql_where=(Column("is_filer_track") == True),
        ),
        DatasetTableBase.__table_args__,
    )

    track_id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)

    is_filer_track: Mapped[bool] = mapped_column()

    # FIXME: should not be nullable but temporarily needs to be until FILER reloaded
    track_type_id: Mapped[int] = ontology_term_fk_column(nullable=True)

    name: Mapped[str]
    description: Mapped[str] = mapped_column(String(2000))

    genome_build: Mapped[str] = enum_column(GenomeBuild)

    feature_type: Mapped[str] = mapped_column(String(50), index=True)
    is_download_only: Mapped[bool] = mapped_column(index=True, nullable=True)

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

    @classmethod
    def _build_record_details(cls, record_source):
        """Build the track details expression used by search results.

        Args:
            record_source: ORM model, CTE, or subquery containing track fields.

        Returns:
            SQLAlchemy expression containing the track name and description.
        """
        record_source = getattr(record_source, "c", record_source)
        return func.jsonb_build_object(
            "label",
            record_source.name,
            "description",
            record_source.description,
        )

    @classmethod
    async def search(
        cls, session: AsyncSession, search_text: str, *, allow_fuzzy: bool = False
    ) -> list[SearchMatch]:
        """Search track metadata using text matching.

        Args:
            session (AsyncSession): Active asynchronous database session.
            search_text (str): Text to search for.
            allow_fuzzy (bool): Whether to include fuzzy matches.

        Returns:
            list[SearchMatch]: Matching track records.
        """
        wildcard_text = f"%{search_text}%"
        cohorts = (
            func.unnest(cls.cohorts).table_valued("cohort").render_derived().lateral()
        )
        match_ctes = []
        for name, field, join_clause in (
            ("source_id", cls.source_id, None),
            ("cohort", cohorts.c.cohort, (cohorts, true())),
        ):
            match_ctes.append(
                cls._build_match_cte(
                    f"exact_{name}_match",
                    MatchType.EXACT_ID,
                    field,
                    func.upper(field) == search_text.upper(),
                    join_clause=join_clause,
                )
            )

        for name, field, match_type in (
            ("name", cls.name, MatchType.PARTIAL_ID),
            ("description", cls.description, MatchType.PARTIAL_DESCRIPTIVE),
        ):
            match_ctes.append(
                cls._build_match_cte(
                    f"partial_{name}_match",
                    match_type,
                    field,
                    field.ilike(wildcard_text),
                )
            )
            if allow_fuzzy:
                match_ctes.append(
                    cls._build_match_cte(
                        f"fuzzy_{name}_match",
                        MatchType.FUZZY_DESCRIPTIVE,
                        field,
                        field.op("%>")(search_text),
                        score=func.word_similarity(search_text, field),
                    )
                )

        for name, match_type, condition in (
            (
                "exact",
                MatchType.EXACT_ID,
                OntologyTerm.term.ilike(search_text),
            ),
            (
                "partial",
                MatchType.PARTIAL_ID,
                OntologyTerm.term.ilike(wildcard_text),
            ),
        ):
            for link_model in (TrackConcept, TrackContext):
                match_ctes.append(
                    cls._build_match_cte(
                        f"{name}_{link_model.__tablename__}_term_match",
                        match_type,
                        OntologyTerm.term,
                        condition,
                        join_clause=(
                            link_model.__table__.join(
                                OntologyTerm,
                                OntologyTerm.ontology_term_id
                                == link_model.ontology_term_id,
                            ),
                            link_model.track_id == cls.track_id,
                        ),
                    )
                )

        matches = union_all(
            *(
                select(
                    match.c.track_id,
                    match.c.source_id,
                    match.c.name,
                    match.c.description,
                    match.c.rank,
                    match.c.score,
                    match.c.matched_text,
                    match.c.match_type,
                )
                for match in match_ctes
            )
        ).cte("matches")
        rank, score, matched_text, match_type = cls._build_windowing_functions(
            matches, record_id=matches.c.track_id
        )
        ranked_tracks = (
            select(
                matches.c.track_id,
                matches.c.source_id,
                matches.c.name,
                matches.c.description,
                rank,
                score,
                matched_text,
                match_type,
            )
            .distinct()
            .subquery("ranked_tracks")
        )
        stmt = select(
            ranked_tracks.c.source_id.label("matched_record_id"),
            literal(str(Entity.TRACK)).label("matched_record_type"),
            cls._build_record_details(ranked_tracks).label("matched_record_details"),
            ranked_tracks.c.rank,
            ranked_tracks.c.score,
            ranked_tracks.c.matched_text,
            ranked_tracks.c.match_type,
        ).order_by(
            ranked_tracks.c.rank.asc(),
            ranked_tracks.c.score.desc(),
            ranked_tracks.c.track_id.asc(),
        )
        rows = (await session.execute(stmt)).mappings().all()
        return [SearchMatch(**row) for row in rows]

    @classmethod
    async def semantic_search(
        cls,
        session: AsyncSession,
        search_text: str,
        embed: EmbeddingFunction,
        *,
        limit: int = 10,
    ) -> list[SearchMatch]:
        """Search track metadata using embedded query text.

        Args:
            session (AsyncSession): Active asynchronous database session.
            search_text (str): Text to embed and search for.
            embed (EmbeddingFunction): Function used to generate embeddings.
            limit (int): Maximum number of results to return.

        Returns:
            list[SearchMatch]: Tracks ranked by semantic similarity.
        """
        raise NotImplementedError("Track semantic search is not implemented.")

    @classmethod
    async def semantic_search_by_embedding(
        cls,
        session: AsyncSession,
        phrase: str,
        embedding: Embedding,
        *,
        limit: int = 10,
    ) -> list[SearchMatch]:
        """Rank tracks by their best matching document chunk.

        Args:
            session (AsyncSession): Active asynchronous database session.
            phrase (str): Text associated with the supplied embedding.
            embedding (Embedding): Precomputed query embedding.
            limit (int): Maximum number of results to return.

        Returns:
            list[SearchMatch]: Tracks ranked by semantic similarity.
        """
        table_ref = await TableCatalog.get_table_ref(session, cls)
        score = 1 - ChunkEmbedding.embedding.cosine_distance(embedding)
        matches = (
            select(
                ChunkMetadata.row_id,
                ChunkMetadata.chunk_text.label("matched_text"),
                score.label("score"),
            )
            .select_from(ChunkEmbedding)
            .join(
                ChunkMetadata,
                ChunkMetadata.chunk_metadata_id == ChunkEmbedding.chunk_metadata_id,
            )
            .where(
                ChunkMetadata.table_id == table_ref.table_id,
            )
            .distinct(ChunkMetadata.row_id)
            .order_by(
                ChunkMetadata.row_id,
                score.desc(),
                ChunkMetadata.chunk_metadata_id.asc(),
            )
            .subquery("semantic_matches")
        )
        stmt = (
            select(
                cls.source_id.label("matched_record_id"),
                cls._build_record_details(cls).label("matched_record_details"),
                literal(str(Entity.TRACK)).label("matched_record_type"),
                matches.c.matched_text,
                literal(MatchType.SEMANTIC.name).label("match_type"),
                literal(MatchType.SEMANTIC.rank() - 1).label("rank"),
                matches.c.score,
            )
            .select_from(matches)
            .join(cls, matches.c.row_id == cls.track_id)
            .order_by(matches.c.score.desc(), cls.track_id.asc())
            .limit(limit)
        )
        rows = (await session.execute(stmt)).mappings().all()
        return [SearchMatch(**row) for row in rows]

    @classmethod
    async def retrieve_records(
        cls, session: AsyncSession, identifiers: list[str]
    ) -> RecordRetrievalResult:
        """Fetch full track records matching source identifiers.

        Args:
            session (AsyncSession): Active asynchronous database session.
            identifiers (list[str]): Track source identifiers to resolve.

        Returns:
            RecordRetrievalResult: Mapping of each requested identifier to
                matching full records.
        """
        mappings = {identifier: [] for identifier in dict.fromkeys(identifiers)}
        lookup_values = cls._build_sql_value_field(list(mappings))
        matches = cls._build_lookup_select(
            lookup_values,
            lookup_field=cls.source_id,
            where_clause=func.upper(cls.source_id)
            == func.upper(lookup_values.c.lookup_value),
        ).subquery("matches")

        for row in await cls._execute_lookup(session, lookup_values, matches):
            record = row["record"]
            if record is not None:
                mappings[row["lookup_value"]].append(record)

        return mappings


class TrackConcept(DatasetTableBase):
    """linking table between Track and OntologyTerm, for MeSH keywords/concepts"""

    _stable_id = None
    __tablename__ = "trackconcept"
    __table_args__ = (
        Index("ix_dataset_trackconcept_term_track", "ontology_term_id", "track_id"),
        DatasetTableBase.__table_args__,
    )
    track_concept_id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    track_id: Mapped[int] = track_fk_column()
    ontology_term_id: Mapped[int] = ontology_term_fk_column()


class TrackContextType(CaseInsensitiveEnum):
    """Defines the metadata context in which an ontology term is associated with a track."""

    BIOSAMPLE = auto()
    PHENOTYPE = auto()
    EXPERIMENT = auto()

    def retrieve_context_from_record(
        self, record: Track
    ) -> Union[BiosampleCharacteristics, Phenotype, ExperimentalDesign]:
        if self is TrackContextType.BIOSAMPLE:
            return record.biosample_characteristics
        if self is TrackContextType.PHENOTYPE:
            return record.participant_phenotypes
        if self is TrackContextType.EXPERIMENT:
            return record.experimental_design


class TrackContext(DatasetTableBase):
    """linking table for deterministic search OntologyTerms nested in metadata JSONB nexted contextual blocks"""

    _stable_id = None
    __tablename__ = "trackcontext"
    __table_args__ = (
        enum_constraint("context", TrackContextType),
        Index("ix_dataset_trackcontext_term_track", "ontology_term_id", "track_id"),
        DatasetTableBase.__table_args__,
    )
    track_context_id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    ontology_term_id: Mapped[int] = ontology_term_fk_column()
    track_id: Mapped[int] = track_fk_column()
    context: Mapped[str] = enum_column(TrackContextType, nullable=False)


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
