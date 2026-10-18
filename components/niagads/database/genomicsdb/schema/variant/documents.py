from typing import Any, Optional

from niagads.common.genomic.regions.models import OneBasedGenomicRegion
from niagads.common.search.models.record import SearchMatch
from niagads.common.search.types import MatchType
from niagads.common.types import Entity, RecordRetrievalResult
from niagads.common.variant.models.annotations import LDPartner
from niagads.common.variant.models.ga4gh_vrs import Allele
from niagads.common.variant.models.record import VariantRecord
from niagads.common.variant.types import VariantClass
from niagads.database.decorators import CompressedJson
from niagads.database.genomicsdb.schema.mixins import (
    IdAliasMixin,
    BulkRecordRetrievalMixin,
    SearchMixin,
)
from niagads.database.genomicsdb.schema.reference.interval_bin import IntervalBin
from niagads.database.genomicsdb.schema.variant.base import VariantTableBase
from niagads.database.genomicsdb.schema.variant.mappings import RefSNPAlias
from niagads.database.mixins.embeddings import EmbeddingMixin
from niagads.database.mixins.ranges import GenomicRegionMixin
from niagads.genome_reference.human import HumanGenome
from niagads.utils.regular_expressions import RegularExpressions
from niagads.utils.string import matches
from sqlalchemy import (
    ForeignKey,
    Integer,
    String,
    Text,
    and_,
    func,
    literal,
    literal_column,
    select,
    union_all,
)
from sqlalchemy.dialects.postgresql import JSONB, Range
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import Mapped, mapped_column


class Variant(
    VariantTableBase,
    IdAliasMixin,
    GenomicRegionMixin,
    EmbeddingMixin,
    SearchMixin,
    BulkRecordRetrievalMixin,
):
    # exclude some fields from mixings
    strand = None
    embedding_model = None
    embedding_date = None

    __tablename__ = "variant"
    __table_args__ = {
        **VariantTableBase.__table_args__,
        "info": {"is_partitioned_by_chromosome": True},
    }

    variant_id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    external_database_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("reference.externaldatabase.external_database_id"),
        nullable=False,
    )
    position: Mapped[int] = mapped_column(nullable=False)
    ref_allele: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    alt_allele: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    length: Mapped[int] = mapped_column(nullable=False)

    niagads_id: Mapped[str] = mapped_column(String(150), nullable=False)
    normalized_positional_id: Mapped[str] = mapped_column(Text, nullable=True)
    ref_snp_id: Mapped[Optional[str]] = mapped_column(String(25), nullable=True)
    ga4gh_vrs: Mapped[Allele] = mapped_column(JSONB(none_as_null=True))
    hgvs: Mapped[Optional[str]] = mapped_column(nullable=True)

    variant_class: Mapped[VariantClass] = mapped_column(String(25), nullable=False)
    is_adsp_variant: Mapped[Optional[bool]] = mapped_column(nullable=True)
    is_structural_variant: Mapped[Optional[bool]] = mapped_column(nullable=True)
    is_annotated: Mapped[Optional[bool]] = mapped_column(nullable=True)

    adsp_annotation: Mapped[Optional[dict]] = mapped_column(
        JSONB(none_as_null=True), nullable=True
    )
    most_severe_consequence: Mapped[Optional[dict]] = mapped_column(
        JSONB(none_as_null=True), nullable=True
    )
    functional_annotation: Mapped[Optional[dict]] = mapped_column(
        JSONB(none_as_null=True), nullable=True
    )
    allele_frequency: Mapped[Optional[dict]] = mapped_column(
        JSONB(none_as_null=True), nullable=True
    )

    ld_partners: Mapped[Optional[list[LDPartner]]] = mapped_column(
        CompressedJson, nullable=True
    )

    functional_annotation_summary: Mapped[Optional[dict]] = mapped_column(
        JSONB(none_as_null=True), nullable=True
    )

    @classmethod
    def from_variant_record(cls, record: VariantRecord):
        return cls(
            chromosome=str(record.chromosome),
            position=record.position,
            span=record.span,
            length=record.length,
            ref_allele=record.ref,
            alt_allele=record.alt,
            variant_class=str(record.variant_class),
            niagads_id=record.id,
            normalized_positional_id=record.normalized_positional_id,
            ref_snp_id=record.ref_snp_id,
            ga4gh_vrs=record.ga4gh_vrs.model_dump(exclude_none=True),
            is_structural_variant=(
                True if record.variant_class.is_structural_variant() else None
            ),
        )

    # -------------------------
    # Search
    # -------------------------

    @classmethod
    async def search(
        cls, session: AsyncSession, search_text: str, *, limit: int = 5
    ) -> list[SearchMatch]:
        """Search variants using deterministic text matching.

        Args:
            session: Active asynchronous database session.
            search_text: Text or identifier to search for.
            limit: Maximum number of matching variants to return.

        Returns:
            RefSNP variants whose identifiers begin with ``search_text``.
        """
        if not search_text or not search_text.lower().startswith("rs"):
            return []

        prefix = func.concat(func.lower(literal(search_text)), literal("%"))
        record_details = func.jsonb_build_object(
            "label",
            cls.ref_snp_id,
            "description",
            cls.variant_class,
        )
        stmt = (
            select(
                cls.niagads_id.label("matched_record_id"),
                record_details.label("matched_record_details"),
                literal(str(Entity.VARIANT)).label("matched_record_type"),
                literal(MatchType.PARTIAL_ID.rank()).label("rank"),
                literal(0.0).label("score"),
                literal(search_text).label("matched_text"),
                literal(MatchType.PARTIAL_ID.name).label("match_type"),
            )
            .where(func.lower(cls.ref_snp_id).like(prefix))
            .order_by(cls.ref_snp_id)
            .limit(limit)
        )
        rows = (await session.execute(stmt)).mappings().all()
        return [SearchMatch(**row) for row in rows]

    @classmethod
    async def semantic_search(
        cls, session, phrase, embed, *, span: OneBasedGenomicRegion, limit=1000
    ):
        """Search variants using an embedded text phrase.

        Args:
            session: Active asynchronous database session.
            phrase: Text phrase to embed and search for.
            embed: Embedding function used to generate the query embedding.
            limit: Maximum number of results to return.
        """
        embedding = embed(phrase)
        return await cls.semantic_search_by_embedding(
            session, phrase, embedding, span=span, limit=limit
        )

    @classmethod
    async def semantic_search_by_embedding(
        cls, session, phrase, embedding, *, span: OneBasedGenomicRegion, limit=10000
    ):
        """Search variants using a precomputed embedding.

        Args:
            session: Active asynchronous database session.
            phrase: Text phrase associated with the embedding.
            embedding: Precomputed query embedding.
            limit: Maximum number of results to return.

        Raises:
            NoResultFound: If no interval bin contains the requested span.
        """
        bin_index = await IntervalBin.find_bin_index(
            session, span.chromosome, span.range
        )
        chromosome = literal_column(f"'{span.chromosome}'")
        parent_bin = literal_column(f"'{bin_index}'::ltree")
        distance = cls.embedding.cosine_distance(embedding)
        score = 1 - distance
        record_details = func.jsonb_build_object(
            "label",
            cls.niagads_id,
            "description",
            cls.variant_class,
            "annotation",
            func.jsonb_build_object(
                "length",
                cls.length,
                "consequence_terms",
                cls.most_severe_consequence["consequence_terms"],
                "impact",
                cls.most_severe_consequence["impact"],
                "is_coding",
                cls.most_severe_consequence["is_coding"],
                "impacted_gene",
                cls.most_severe_consequence["impacted_gene"],
            ),
        )

        stmt = (
            select(
                cls.niagads_id.label("matched_record_id"),
                record_details.label("matched_record_details"),
                literal(str(Entity.VARIANT)).label("matched_record_type"),
                literal(MatchType.SEMANTIC.rank()).label("rank"),
                score.label("score"),
                literal(phrase).label("matched_text"),
                literal(MatchType.SEMANTIC.name).label("match_type"),
            )
            .where(
                and_(
                    cls.chromosome == chromosome,
                    parent_bin.op("@>")(cls.bin_index),
                    cls.span.op("&&")(span.range),
                    cls.embedding.is_not(None),
                )
            )
            .order_by(distance.asc())
            .limit(limit)
        )
        rows = (await session.execute(stmt)).mappings().all()
        return [SearchMatch(**row) for row in rows]

    # -------------------------
    # Record Retrieval
    # -------------------------

    @classmethod
    async def _find_current_ref_snp(
        cls, session: AsyncSession, ref_snp_ids: list[str]
    ) -> dict[str, Optional[str]]:
        """Resolve RefSNP IDs through the complete merge hierarchy.

        Args:
            session (AsyncSession): Active asynchronous database session.
            ref_snp_ids (list[str]): RefSNP identifiers to resolve.

        Returns:
            dict[str, Optional[str]]: Mapping of each requested RefSNP ID to its
            current ID, or ``None`` when no merge record exists.
        """
        if not ref_snp_ids:
            return {}

        queried = cls._build_sql_value_field(ref_snp_ids).cte("queried")
        merges = (
            select(
                queried.c.lookup_value.label("queried_id"),
                RefSNPAlias.ref_snp_id,
                RefSNPAlias.merged_into,
                RefSNPAlias.merge_build,
            )
            .select_from(
                queried.join(
                    RefSNPAlias,
                    func.lower(RefSNPAlias.ref_snp_id)
                    == func.lower(queried.c.lookup_value),
                )
            )
            .cte("merges", recursive=True)
        )
        merges = merges.union(
            select(
                merges.c.queried_id,
                RefSNPAlias.ref_snp_id,
                RefSNPAlias.merged_into,
                RefSNPAlias.merge_build,
            ).select_from(
                merges.join(
                    RefSNPAlias,
                    func.lower(RefSNPAlias.ref_snp_id)
                    == func.lower(merges.c.merged_into),
                )
            )
        )

        results = union_all(
            select(
                merges.c.queried_id,
                merges.c.merged_into,
                merges.c.merge_build,
            ),
            select(
                queried.c.lookup_value,
                queried.c.lookup_value,
                literal(-1),  # not matched
            ),
        ).subquery("results")
        stmt = (
            select(
                results.c.queried_id,
                results.c.merged_into,
                results.c.merge_build,
            )
            .distinct(results.c.queried_id)
            .order_by(results.c.queried_id, results.c.merge_build.desc())
        )
        rows = (await session.execute(stmt)).mappings()
        return {
            row["queried_id"]: (
                None if row["merge_build"] == -1 else row["merged_into"]
            )
            for row in rows
        }

    @classmethod
    async def _execute_ref_snp_id_lookup(cls, session, ref_snp_ids: list[str]):
        """Execute a direct lookup for RefSNP identifiers.

        Args:
            session (AsyncSession): Active asynchronous database session.
            ref_snp_ids (list[str]): RefSNP identifiers to look up.

        Returns:
            Mapping result rows containing each lookup identifier and matching
            variant record, or a null record for unmatched identifiers.
        """

        ref_snp_lookup_values = cls._build_sql_value_field(ref_snp_ids)
        ref_snp_select = cls._build_lookup_select(
            ref_snp_lookup_values,
            lookup_field=cls.ref_snp_id,
            where_clause=func.lower(cls.ref_snp_id)
            == func.lower(ref_snp_lookup_values.c.lookup_value),
        )
        return await cls._execute_lookup(
            session,
            ref_snp_lookup_values,
            ref_snp_select.subquery("ref_snp_matches"),
        )

    @classmethod
    async def _fetch_records_by_ref_snp_id(cls, session, mappings: dict[str, Any]):
        """Populate lookups with direct and merged RefSNP matches.

        Args:
            session (AsyncSession): Active asynchronous database session.
            mappings (dict[str, Any]): Mapping of requested identifiers to
                resolved records, updated in place.
        """
        ref_snp_ids = [
            variant_id
            for variant_id in mappings
            if matches(RegularExpressions.REF_SNP_ID, variant_id.lower())
        ]
        if not ref_snp_ids:
            return

        not_matched = []
        for row in await cls._execute_ref_snp_id_lookup(session, ref_snp_ids):
            record = row["record"]
            variant_id = row["lookup_value"]
            if record is None:
                not_matched.append(variant_id)
            else:
                mappings[variant_id].append(record)

        if not_matched:
            alias_mapping = await cls._find_current_ref_snp(session, not_matched)
            aliased_ref_snp_ids = [v for v in alias_mapping.values() if v is not None]
            alias_reverse_mapping = {
                v: k for k, v in alias_mapping.items() if v is not None
            }
            for row in await cls._execute_ref_snp_id_lookup(
                session, aliased_ref_snp_ids
            ):
                record = row["record"]
                if record is not None:
                    alias_id = row["lookup_value"]
                    original_variant_id = alias_reverse_mapping[alias_id]
                    mappings[original_variant_id].append(record)

    @classmethod
    async def _execute_positional_id_lookup(cls, session, positional_ids: list[str]):
        """Execute a chromosome-aware lookup for positional variant IDs.

        Args:
            session (AsyncSession): Active asynchronous database session.
            positional_ids (list[tuple[str, str]]): Positional identifiers paired
                with chromosomes.

        Returns:
            Mapping result rows containing each lookup identifier and matching
            variant record, or a null record for unmatched identifiers.
        """

        positional_lookup_values = cls._build_sql_value_field(
            [identifier for identifier, _ in positional_ids]
        )
        positional_chromosomes = {
            literal_column(f"'{chromosome}'") for _, chromosome in positional_ids
        }
        positional_select = cls._build_lookup_select(
            positional_lookup_values,
            lookup_field=cls.niagads_id,
            where_clause=and_(
                cls.niagads_id == positional_lookup_values.c.lookup_value,
                cls.chromosome.in_(positional_chromosomes),
            ),
        )
        return await cls._execute_lookup(
            session,
            positional_lookup_values,
            positional_select.subquery("positional_matches"),
        )

    @classmethod
    async def _fetch_records_by_positional_id(cls, session, mappings: dict[str, Any]):
        """Populate lookups with positional variant matches.

        Exact positional matches are attempted first. Unmatched SNVs are then
        retried with their reference and alternate alleles switched.

        Args:
            session (AsyncSession): Active asynchronous database session.
            mappings (dict[str, Any]): Mapping of requested identifiers to
                resolved records, updated in place.
        """
        positional_ids = [
            (
                variant_id,
                str(HumanGenome(variant_id.split(":", 1)[0].lower())),
            )
            for variant_id in mappings
            if matches(RegularExpressions.POSITIONAL_VARIANT_ID, variant_id)
        ]

        if not positional_ids:
            return

        not_matched = []
        for row in await cls._execute_positional_id_lookup(session, positional_ids):
            record = row["record"]
            variant_id = row["lookup_value"]
            if record is None:
                chrm, pos, ref, alt = variant_id.split(":")
                if len(ref) == 1 and len(alt) == 1:  # SNV
                    not_matched.append(
                        (
                            f"{chrm}:{pos}:{alt}:{ref}",
                            str(HumanGenome(chrm)),
                        )
                    )

            else:
                mappings[variant_id].append(record)

        if not_matched:
            for row in await cls._execute_positional_id_lookup(
                session,
                [
                    (swapped_identifier, chromosome)
                    for _, swapped_identifier, chromosome in not_matched
                ],
            ):
                record = row["record"]
                if record is not None:
                    chrm, pos, alt, ref = row["lookup_value"].split(":")
                    variant_id = f"{chrm}:{pos}:{ref}:{alt}"
                    mappings[variant_id].append(record)

    @classmethod
    async def _fetch_records_by_structural_variant_id(
        cls, session, mappings: dict[str, Any]
    ):
        """Populate lookups with structural variant matches.

        Args:
            session (AsyncSession): Active asynchronous database session.
            mappings (dict[str, Any]): Mapping of requested identifiers to
                resolved records, updated in place.
        """
        structural_variant_ids = [
            (
                variant_id,
                str(HumanGenome(variant_id.split("_")[1].lower())),
            )
            for variant_id in mappings
            if matches(RegularExpressions.STRUCTUAL_VARIANT_ID, variant_id.upper())
        ]

        if not structural_variant_ids:
            return

        sql_value_array = cls._build_sql_value_field(
            [variant_id for variant_id, _ in structural_variant_ids]
        )
        chromosomes = {
            literal_column(f"'{chromosome}'")
            for _, chromosome in structural_variant_ids
        }

        structural_select = cls._build_lookup_select(
            sql_value_array,
            lookup_field=cls.niagads_id,
            where_clause=and_(
                func.upper(cls.niagads_id)
                == func.upper(sql_value_array.c.lookup_value),
                cls.chromosome.in_(chromosomes),
                cls.is_structural_variant.is_(True),
            ),
        )

        for row in await cls._execute_lookup(
            session,
            sql_value_array,
            structural_select.subquery("structural_variant_id_matches"),
        ):
            record = row["record"]
            if record is not None:
                variant_id = row["lookup_value"]
                mappings[variant_id].append(record)

    @classmethod
    async def retrieve_records(
        cls, session: AsyncSession, identifiers: list[str]
    ) -> RecordRetrievalResult:
        """Fetch variants matching one or more identifiers.

        Args:
            session (AsyncSession): Active asynchronous database session.
            variant_ids (list[str]): Variant identifiers to resolve.

        Returns:
            RecordRetrievalResult: Mapping of each requested identifier to
                matching full records.

        Notes:
            RefSNP aliases are resolved only for identifiers not found directly. This
            keeps the common RefSNP lookup on the indexed variant table and avoids an
            unnecessary join to the merge-history table.
        """
        mappings = {identifier: [] for identifier in dict.fromkeys(identifiers)}
        await cls._fetch_records_by_ref_snp_id(session, mappings)
        await cls._fetch_records_by_positional_id(session, mappings)
        await cls._fetch_records_by_structural_variant_id(session, mappings)

        return mappings
