"""
Materialized view and document-oriented ORM definitions for gene-centric RAG (Retrieval-Augmented Generation) documents.

Defines the RAG document materialized view and related fields for querying gene knowledge in the genomicsdb gene schema.
"""

from typing import Optional

from niagads.common.search.models.record import SearchMatch
from niagads.common.search.types import MatchType
from niagads.common.types import Entity, RecordRetrievalResult
from niagads.database.genomicsdb.schema.admin.catalog import TableCatalog
from niagads.database.genomicsdb.schema.gene.base import GeneMaterializedViewBase
from niagads.database.genomicsdb.schema.gene.structure import GeneModel
from niagads.database.genomicsdb.schema.gene.xrefs import (
    SYNONYM_FIELDS,
    GeneIdentifierType,
    GeneXRef,
)
from niagads.database.genomicsdb.schema.mixins import (
    IdAliasMixin,
    BulkRecordRetrievalMixin,
    SearchMixin,
)
from niagads.database.genomicsdb.schema.ragdoc.chunks import (
    ChunkEmbedding,
    ChunkMetadata,
)
from niagads.database.genomicsdb.schema.ragdoc.types import GeneDocumentSection
from niagads.database.mixins import GenomicRegionMixin
from sqlalchemy import (
    String,
    and_,
    func,
    literal,
    select,
    union,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import Mapped, mapped_column


class Gene(
    GeneMaterializedViewBase,
    GenomicRegionMixin,
    IdAliasMixin,
    SearchMixin,
    BulkRecordRetrievalMixin,
):
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
    def _build_record_details(cls, record_source):
        """Build the JSON record details expression used by gene searches.

        Args:
            record_source: ORM model, CTE, or subquery containing gene fields.

        Returns:
            SQLAlchemy expression producing the gene label, description, and
            annotation fields.
        """
        record_source = getattr(record_source, "c", record_source)
        return func.jsonb_build_object(
            "label",
            record_source.nomenclature["gene_symbol"].astext,
            "description",
            record_source.nomenclature["gene_name"].astext,
            "annotation",
            func.jsonb_build_object(
                "gene_type",
                record_source.gene_type,
                "location",
                func.concat_ws(
                    " // ",
                    record_source.gene_structure["location"].astext,
                    record_source.gene_structure["cytogenic_location"].astext,
                ),
            ),
        )

    @classmethod
    async def search(cls, session: AsyncSession, search_text) -> SearchMatch:

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
            record_details=cls._build_record_details(matches_cte),
            record_type=Entity.GENE,
        )

    @classmethod
    async def semantic_search(
        cls,
        session,
        phrase,
        embed,
        *,
        limit=10,
        sections: list[GeneDocumentSection] = None,
    ):
        embedding = embed(phrase)
        return cls.semantic_search_by_embedding(
            session, phrase, embedding, limit=limit, sections=sections
        )

    @classmethod
    async def semantic_search_by_embedding(
        cls,
        session,
        phrase,
        embedding,
        *,
        limit=10,
        sections: list[GeneDocumentSection] = None,
    ):
        table_ref = await TableCatalog.get_table_ref(session, cls)
        score = 1 - ChunkEmbedding.embedding.cosine_distance(embedding)
        where_clause = ChunkMetadata.table_id == table_ref.table_id
        if sections:
            where_clause = and_(
                where_clause,
                ChunkMetadata.document_section.in_(
                    [str(section) for section in sections]
                ),
            )

        matches = (
            select(
                cls.source_id.label("record_id"),
                cls._build_record_details(cls).label("record_details"),
                literal(str(Entity.GENE)).label("record_type"),
                literal(MatchType.SEMANTIC.rank()).label("rank"),
                score.label("score"),
                literal(phrase).label("matched_text"),
                literal(MatchType.SEMANTIC.name).label("match_type"),
            )
            .select_from(ChunkEmbedding)
            .join(
                ChunkMetadata,
                ChunkMetadata.chunk_metadata_id == ChunkEmbedding.chunk_metadata_id,
            )
            .join(cls, ChunkMetadata.row_id == cls.gene_id)
            .where(where_clause)
        ).subquery("semantic_matches")

        rank, score, matched_text, match_type = cls._build_windowing_functions(
            matches,
            record_id=matches.c.record_id,
        )

        stmt = (
            select(
                matches.c.record_id,
                matches.c.record_details,
                matches.c.record_type,
                rank,
                score,
                matched_text,
                match_type,
            )
            .distinct()
            .order_by(rank.asc(), score.desc())
            .limit(limit)
        )

        rows = (await session.execute(stmt)).mappings().all()
        return [SearchMatch(**row) for row in rows]

    @classmethod
    async def retrieve_records(
        cls, session, identifiers: list[str]
    ) -> RecordRetrievalResult:
        """Fetch gene documents matching one or more identifiers.

        Args:
            session (AsyncSession): Active asynchronous database session.
            identifiers (list[str]): Gene identifiers, symbols, or synonyms to
                resolve.

        Returns:
            RecordRetrievalResult: Mapping of each identifier to matching gene
                records.
        """

        mappings = {identifier: [] for identifier in dict.fromkeys(identifiers)}

        sql_value_array = cls._build_sql_value_field(identifiers)

        source_select = cls._build_lookup_select(
            sql_value_array,
            lookup_field=cls.source_id,
        )
        symbol_select = cls._build_lookup_select(
            sql_value_array,
            lookup_field=cls.nomenclature["gene_symbol"].astext,
            where_clause=cls.nomenclature["gene_symbol"].astext.ilike(
                sql_value_array.c.lookup_value
            ),
        )
        synonym_select = cls._build_lookup_select(
            sql_value_array,
            lookup_field=GeneXRef.xref_value,
            where_clause=GeneXRef.xref_label.in_(SYNONYM_FIELDS),
            join_clause=[
                (
                    GeneXRef,
                    GeneXRef.xref_value == sql_value_array.c.lookup_value,
                ),
                (cls, GeneXRef.gene_id == cls.gene_id),
            ],
        )

        matches = union(
            source_select,
            symbol_select,
            synonym_select,
        ).subquery("matches")

        for row in await cls._execute_lookup(
            session,
            sql_value_array,
            matches,
        ):
            record = row["record"]
            if record is not None:
                gene_id = row["lookup_value"]
                mappings[gene_id].append(record)

        return mappings

    # -------------------------
    # Lookup
    # -------------------------
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
