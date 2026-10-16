from typing import Any, Optional

from niagads.common.search.models.record import SearchMatch
from niagads.common.variant.models.annotations import LDPartner
from niagads.common.variant.models.ga4gh_vrs import Allele
from niagads.common.variant.models.record import VariantRecord
from niagads.common.variant.types import VariantClass
from niagads.database.decorators import CompressedJson
from niagads.database.genomicsdb.schema.mixins import (
    IdAliasMixin,
    RecordRetrievalMixin,
    SearchMixin,
)
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
    literal,
    literal_column,
    select,
    union_all,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import Mapped, mapped_column


class Variant(
    VariantTableBase,
    IdAliasMixin,
    GenomicRegionMixin,
    EmbeddingMixin,
    SearchMixin,
    RecordRetrievalMixin,
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
    async def search(cls, session: AsyncSession, search_text) -> SearchMatch:
        """Search variants using deterministic text matching.

        Args:
            session: Active asynchronous database session.
            search_text: Text or identifier to search for.

        Raises:
            NotImplementedError: Variant text search is not implemented.
        """
        raise NotImplementedError()

    @classmethod
    async def semantic_search(cls, session, phrase, embed, *, limit=10):
        """Search variants using an embedded text phrase.

        Args:
            session: Active asynchronous database session.
            phrase: Text phrase to embed and search for.
            embed: Embedding function used to generate the query embedding.
            limit: Maximum number of results to return.

        Raises:
            NotImplementedError: Variant semantic search is not implemented.
        """
        raise NotImplementedError()

    @classmethod
    async def semantic_search_by_embedding(
        cls, session, phrase, embedding, *, limit=10
    ):
        """Search variants using a precomputed embedding.

        Args:
            session: Active asynchronous database session.
            phrase: Text phrase associated with the embedding.
            embedding: Precomputed query embedding.
            limit: Maximum number of results to return.

        Raises:
            NotImplementedError: Variant semantic search is not implemented.
        """
        raise NotImplementedError()

    # -------------------------
    # Record Retrieval
    # -------------------------

    @classmethod
    async def _find_current_ref_snp(
        cls, session: AsyncSession, ref_snp_ids: list[str]
    ) -> dict[str, Optional[str]]:
        """Resolve RefSNP IDs through the complete merge hierarchy.

        Args:
            session: Active asynchronous database session.
            ref_snp_ids: RefSNP identifiers to resolve.

        Returns:
            Mapping of each requested RefSNP ID to its current ID, or ``None``
            when no merge record exists.
        """
        if not ref_snp_ids:
            return {}

        queried = cls._build_lookup_values(ref_snp_ids).cte("queried")
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
                    RefSNPAlias.ref_snp_id == queried.c.lookup_value,
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
                    RefSNPAlias.ref_snp_id == merges.c.merged_into,
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
            session: Active asynchronous database session.
            ref_snp_ids: RefSNP identifiers to look up.

        Returns:
            Mapping of each identifier to matching variant records, or ``None``.
        """
        if not ref_snp_ids:
            return
        ref_snp_lookup_values = cls._build_lookup_values(ref_snp_ids)
        ref_snp_select = cls._build_lookup_select(
            ref_snp_lookup_values,
            lookup_field=cls.ref_snp_id,
        )
        return await cls._execute_lookup(
            session,
            ref_snp_lookup_values,
            ref_snp_select.subquery("ref_snp_matches"),
            ref_snp_ids,
        )

    @classmethod
    async def _fetch_records_by_ref_snp_id(cls, session, lookups: dict[str, Any]):
        """Populate lookups with direct and merged RefSNP matches.

        Args:
            session: Active asynchronous database session.
            lookups: Mapping of requested identifiers to resolved records.
        """
        ref_snp_ids = [
            identifier.lower()
            for identifier in lookups
            if matches(RegularExpressions.REF_SNP_ID, identifier.lower())
        ]
        id_matches = await cls._execute_ref_snp_id_lookup(session, ref_snp_ids)

        not_matched = []
        for identifier in lookups:
            normalized_identifier = identifier.lower()
            if normalized_identifier in id_matches:
                lookups[identifier] = id_matches[normalized_identifier]
            else:
                not_matched.append(normalized_identifier)

        if not_matched:
            aliases = await cls._find_current_ref_snp(session, not_matched)
            ref_snp_ids = [v for v in aliases.values() if v is not None]
            id_matches = await cls._execute_ref_snp_id_lookup(session, ref_snp_ids)
            for alias, current_id in aliases.items():
                if current_id is not None:
                    records = id_matches.get(current_id)
                    if records is not None:
                        lookups[alias] = records

    @classmethod
    async def _execute_positional_id_lookup(cls, session, positional_ids: list[str]):
        """Execute a chromosome-aware lookup for positional variant IDs.

        Args:
            session: Active asynchronous database session.
            positional_ids: Positional identifiers paired with chromosomes.

        Returns:
            Mapping of each positional identifier to matching variant records,
            or ``None``.
        """
        if not positional_ids:
            return
        positional_lookup_values = cls._build_lookup_values(
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
            [identifier for identifier, _ in positional_ids],
        )

    @classmethod
    async def _fetch_records_by_positional_id(cls, session, lookups: dict[str, Any]):
        """Populate lookups with positional variant matches.

        Exact positional matches are attempted first. Unmatched SNVs are then
        retried with their reference and alternate alleles switched.

        Args:
            session: Active asynchronous database session.
            lookups: Mapping of requested identifiers to resolved records.
        """
        positional_ids = [
            (
                identifier,
                str(HumanGenome(identifier.split(":", 1)[0].lower())),
            )
            for identifier in lookups
            if matches(RegularExpressions.POSITIONAL_VARIANT_ID, identifier)
        ]

        id_matches = await cls._execute_positional_id_lookup(session, positional_ids)

        not_matched = []
        for identifier, chromosome in positional_ids:
            if id_matches[identifier] is not None:
                lookups[identifier] = id_matches[identifier]
            else:
                chrm, pos, ref, alt = identifier.split(":")
                if len(ref) == 1 and len(alt) == 1:  # SNV
                    not_matched.append(
                        (
                            identifier,
                            f"{chrm}:{pos}:{alt}:{ref}",
                            chromosome,
                        )
                    )

        if not_matched:
            swapped_matches = await cls._execute_positional_id_lookup(
                session,
                [
                    (swapped_identifier, chromosome)
                    for _, swapped_identifier, chromosome in not_matched
                ],
            )
            for identifier, swapped_identifier, _ in not_matched:
                if swapped_matches[swapped_identifier] is not None:
                    lookups[identifier] = swapped_matches[swapped_identifier]

    @classmethod
    async def fetch_records_by_identifier(
        cls, session: AsyncSession, identifiers: list[str]
    ) -> dict[str, list[dict] | None]:
        """Fetch variants matching one or more identifiers.

        Args:
            session: Active asynchronous database session.
            identifiers: Variant identifiers to resolve.

        Returns:
            Mapping of each requested identifier to matching full records, or ``None``.

        Notes:
            RefSNP aliases are resolved only for identifiers not found directly. This
            keeps the common RefSNP lookup on the indexed variant table and avoids an
            unnecessary join to the merge-history table.
        """
        lookups = {identifier: None for identifier in dict.fromkeys(identifiers)}
        await cls._fetch_records_by_ref_snp_id(
            lookups,
        )

        """
            elif matches(RegularExpressions.STRUCTUAL_VARIANT_ID, identifier.upper()):
                structural_id = identifier.upper()
                structural_variant_ids.append(
                    (
                        structural_id,
                        str(HumanGenome(structural_id.split("_")[1].lower())),
                    )
                )
            elif matches(RegularExpressions.POSITIONAL_VARIANT_ID, identifier):
                positional_ids.append(
                    (identifier, str(HumanGenome(identifier.split(":")[1].lower())))
                )

        if ref_snp_ids:
            cls._fetch_records_by_ref_snp_id(session, identifiers)
            
        if structural_variant_ids:
            structural_lookup_values = cls._build_lookup_values(
                [identifier for identifier, _ in structural_variant_ids]
            )
            # Developer note: use SQL literals for partition pruning. These values
            # come from the controlled HumanGenome enum, so they are trusted.
            structural_chromosomes = {
                literal_column(f"'{chromosome}'")
                for _, chromosome in structural_variant_ids
            }
            structural_select = cls._build_lookup_select(
                structural_lookup_values,
                lookup_field=cls.niagads_id,
                where_clause=and_(
                    cls.niagads_id == structural_lookup_values.c.lookup_value,
                    cls.chromosome.in_(structural_chromosomes),
                    cls.is_structural_variant.is_(True),
                ),
            )

        if positional_ids:
            positional_lookup_values = cls._build_lookup_values(
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

        # TODO: add fallback check for unmatched non-SNV positional_ids against normalized positional ids
        return lookup
        """
