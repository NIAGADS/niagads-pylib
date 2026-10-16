"""
Materialized view and document-oriented ORM definitions for gene-centric RAG (Retrieval-Augmented Generation) documents.

Defines the RAG document materialized view and related fields for querying gene knowledge in the genomicsdb gene schema.
"""

from typing import Optional

from niagads.common.search.models.record import LookupMatch
from niagads.common.search.types import MatchType
from niagads.common.types import Entity
from niagads.database.genomicsdb.schema.gene.base import GeneMaterializedViewBase
from niagads.database.genomicsdb.schema.gene.structure import GeneModel
from niagads.database.genomicsdb.schema.gene.xrefs import (
    SYNONYM_FIELDS,
    GeneIdentifierType,
    GeneXRef,
)
from niagads.database.genomicsdb.schema.mixins import IdAliasMixin, SearchMixin
from niagads.database.mixins import GenomicRegionMixin
from sqlalchemy import String, and_, func, select, union
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import Mapped, mapped_column


class Gene(GeneMaterializedViewBase, GenomicRegionMixin, IdAliasMixin, SearchMixin):
    __tablename__ = "document_mv"

    # The view contains the genomic interval fields but not strand.
    strand = None

    __table_args__ = (
        *GenomicRegionMixin.get_indexes(
            GeneMaterializedViewBase._schema, __tablename__
        ),
        GeneMaterializedViewBase.__table_args__,
    )

    gene_id: Mapped[int] = mapped_column(index=True, primary_key=True)  # not PK b/c MV
    source_id: Mapped[str] = mapped_column(String(50), index=True, nullable=False)
    nomenclature: Mapped[Optional[dict]] = mapped_column(
        JSONB(none_as_null=True), nullable=True
    )
    gene_structure: Mapped[Optional[dict]] = mapped_column(
        JSONB(none_as_null=True), nullable=True
    )
    gene_type: Mapped[str] = mapped_column()
    xrefs: Mapped[Optional[dict]] = mapped_column(
        JSONB(none_as_null=True), nullable=True
    )
    publications: Mapped[Optional[list]] = mapped_column(
        JSONB(none_as_null=True), nullable=True
    )
    memberships: Mapped[Optional[dict]] = mapped_column(
        JSONB(none_as_null=True), nullable=True
    )
    functional_annotation: Mapped[Optional[list]] = mapped_column(
        JSONB(none_as_null=True), nullable=True
    )
    associated_with_known_ad_locus: Mapped[bool] = mapped_column(
        index=True, nullable=False
    )

    # -------------------------
    # Search
    # -------------------------

    @classmethod
    async def search(cls, session: AsyncSession, search_text) -> LookupMatch:

        # exact matches
        exact_id_match_cte = cls._build_match_cte(
            "exact_id_match",
            MatchType.EXACT_ID,
            Gene.source_id,
            Gene.source_id.ilike(search_text),
        )

        exact_symobl_match_cte = cls._build_match_cte(
            "exact_symbol_match",
            MatchType.EXACT_ID,
            Gene.nomenclature["gene_symbol"].astext,
            Gene.nomenclature["gene_symbol"].astext.ilike(search_text),
        )

        exact_synomym_match_cte = cls._build_match_cte(
            "exact_synonym_match",
            MatchType.EXACT_ID,
            GeneXRef.xref_value,
            and_(
                GeneXRef.xref_label.in_(SYNONYM_FIELDS),
                GeneXRef.xref_value.ilike(search_text),
            ),
            join_clause=(
                GeneXRef,
                GeneXRef.gene_id == cls.gene_id,
            ),
        )

        # partial matchees
        wildcard_phrase = f"%{search_text}%"
        partial_id_match_cte = cls._build_match_cte(
            "partial_id_match",
            MatchType.PARTIAL_ID,
            Gene.source_id,
            Gene.source_id.ilike(wildcard_phrase),
        )

        partial_symbol_match_cte = cls._build_match_cte(
            "partial_symbol_match",
            MatchType.PARTIAL_ID,
            Gene.nomenclature["gene_symbol"].astext,
            Gene.nomenclature["gene_symbol"].astext.ilike(search_text),
        )

        partial_synomym_match_cte = cls._build_match_cte(
            "partial_synonym_match",
            MatchType.EXACT_ID,
            GeneXRef.xref_value,
            and_(
                GeneXRef.xref_label.in_(SYNONYM_FIELDS),
                GeneXRef.xref_value.ilike(wildcard_phrase),
            ),
            join_clause=(
                GeneXRef,
                GeneXRef.gene_id == cls.gene_id,
            ),
        )

        # fuzzy match against gene name
        fuzzy_name_match_cte = cls._build_match_cte(
            "fuzzy_name_match",
            MatchType.FUZZY_DESCRIPTIVE,
            GeneModel.gene_name,
            and_(
                GeneModel.gene_name.definition.op("%")(search_text),
                func.similarity(GeneModel.gene_name, search_text) >= 0.5,
            ),
            score=func.similarity(GeneModel.gene_name, search_text),
            join_clause=(
                GeneModel,
                GeneModel.gene_id == cls.gene_id,
            ),
        )

        matches_cte = union(
            select(exact_id_match_cte),
            select(exact_symobl_match_cte),
            select(exact_synomym_match_cte),
            select(partial_id_match_cte),
            select(partial_symbol_match_cte),
            select(partial_synomym_match_cte),
            select(fuzzy_name_match_cte),
        ).cte("matches")

        return await cls._execute_search(
            session,
            matches_cte,
            record_id=matches_cte.c.source_id,
            record_details=func.jsonb_build_object(
                "label",
                matches_cte.c.nomenclature["gene_symbol"].astext,
                "description",
                matches_cte.c.nomenclature["gene_name"].astext,
                "annotation",
                func.jsonb_build_object(
                    "gene_type",
                    matches_cte.c.gene_type,
                    "location",
                    func.concat_ws(
                        " // ",
                        matches_cte.c.gene_structure["location"].astext,
                        matches_cte.c.gene_structure["cytogenic_location"].astext,
                    ),
                ),
            ),
            record_type=Entity.GENE,
        )

    @classmethod
    async def resolve_identifier(
        cls,
        session: AsyncSession,
        id: str,
        gene_identifier_type: GeneIdentifierType,
        require_exact_match: bool = True,
        allow_multiple: bool = False,
    ):
        """
        Resolve a gene to its primary key by a given identifier and identifier type.
        Only does exact matching to identifier

        Supports lookup by Ensembl ID, gene symbol (not implemented), and a select set
        of XRefs (GeneIdentifierType)

        Args:
            session (AsyncSession): SQLAlchemy async session for database
                access.
            id (str): The identifier value to resolve (e.g., Ensembl ID,
                HGNC ID).
            gene_identifier_type (GeneIdentifierType): The type of identifier
                to use for lookup.
            require_exact_match (Optional, bool): flag indicating whether exact matches are required
                applicable to gene symbols (if false will do case insensitive match and search
                synonyms).  Defaults to True
            allow_multiple (Optional, bool): flag indicating whether to fail on multiple matches.
                Defaults to False


        Returns:
            int, list[int]: the primary key for the gene record (or list of primary keys if `allow_multiple`)

        Raises:
            NoResultFound: If no matching record is found for the given
                identifier.
            MultipleResultsFound: If multiple records are found for the given
                identifier.

        Example:
            await gene.resolve_identifier(
                session, "ENSG00000123456", GeneIdentifierType.ENSEMBL
            )
        """
        #  want to be able to look these up even if document MV is out of date
        if gene_identifier_type == GeneIdentifierType.ENSEMBL:
            return await GeneModel.find_primary_key(
                session, {"source_id": id.upper()}, allow_multiple=allow_multiple
            )
        elif gene_identifier_type == GeneIdentifierType.SYMBOL and require_exact_match:
            return await GeneModel.find_primary_key(
                session, {"gene_symbol": id}, allow_multiple=allow_multiple
            )

        else:  # ditto
            return await GeneXRef.resolve_identifier(
                session,
                id,
                gene_identifier_type,
                require_exact_match=require_exact_match,
                allow_multiple=allow_multiple,
            )
