"""
Materialized view and document-oriented ORM definitions for gene-centric RAG (Retrieval-Augmented Generation) documents.

Defines the RAG document materialized view and related fields for querying gene knowledge in the genomicsdb gene schema.
"""

from typing import Optional, Self, cast

from niagads.common.models.composite_attributes.gene import (
    GOAnnotation,
    PathwayAnnotation,
)
from niagads.database.mixins.ranges import GenomicRegionMixin
from niagads.genomicsdb.schema.gene.base import GeneMaterializedViewBase
from niagads.genomicsdb.schema.gene.xrefs import GeneXRefType
from niagads.genomicsdb.schema.mixins import IdAliasMixin
from sqlalchemy import ARRAY, String, func, or_, select
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.exc import MultipleResultsFound, NoResultFound
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import Mapped, mapped_column


class Gene(GeneMaterializedViewBase, GenomicRegionMixin, IdAliasMixin):
    __tablename__ = "document_mv"

    gene_id: Mapped[int] = mapped_column(index=True)  # not PK b/c MV
    ensembl_id: Mapped[str] = mapped_column(uniuqe=True, index=True)
    symbol: Mapped[str] = mapped_column(String(50))
    name: Mapped[str] = mapped_column(String(250))
    gene_type: Mapped[str] = mapped_column(String(150))
    synonyms: Mapped[list[str]] = mapped_column(ARRAY(String), nullable=True)
    cytogenic_location: str = mapped_column(String(100), index=True)
    xrefs: Mapped[dict] = mapped_column(JSONB)
    go_annotation: Mapped[Optional[GOAnnotation]] = mapped_column(
        JSONB(none_as_null=True)
    )
    pathway_membership: Mapped[Optional[PathwayAnnotation]]
    data_sources: Mapped[dict] = mapped_column(JSONB)

    async def __resolve_synonyms(
        self, session: AsyncSession, id: str, case_insensitive: bool = False
    ):
        """
        Resolve a gene record by its synonym, with optional case-insensitive
        matching.

        Args:
            session (AsyncSession): SQLAlchemy async session for database
                access.
            id (str): The synonym to resolve.
            case_insensitive (bool, optional): If True, perform
                case-insensitive matching. Defaults to False.

        Returns:
            dict: Dictionary containing the primary key (gene_id) and stable
                identifier (ensembl_id) for the resolved gene record.

        Raises:
            NoResultFound: If no matching record is found for the given
                synonym.
            MultipleResultsFound: If multiple records are found for the given
                synonym.
        """
        if case_insensitive:
            where_clause = func.lower(id) == func.any_(func.lower(Gene.synonyms))
        else:
            where_clause = id == func.any_(Gene.synonyms)

        stmt = select(Gene).where(where_clause)
        result = await session.execute(stmt)
        rows = result.scalars().all()
        if not rows:
            raise NoResultFound(
                f"No record for symbol '{id}' found in {self.table_name()}"
            )
        if len(rows) > 1:
            raise MultipleResultsFound(
                f"Multiple records found for symbol '{id}' in {self.table_name()}"
            )

        record: Self = cast(Self, rows[0])
        return {"gene_id": record.gene_id, "ensembl_id": record.ensembl_id}

    async def resolve_gene_symobl(
        self, session: AsyncSession, id: str, case_insensitive: bool = False
    ):
        """
        Resolve a gene record by its symbol, with optional case-insensitive
        matching. If no symbol match is found, attempts to resolve by synonym.

        Args:
            session (AsyncSession): SQLAlchemy async session for database
                access.
            id (str): The gene symbol to resolve.
            case_insensitive (bool, optional): If True, perform
                case-insensitive matching. Defaults to False.

        Returns:
            dict: Dictionary containing the primary key (gene_id) and stable
                identifier (ensembl_id) for the resolved gene record.

        Raises:
            NoResultFound: If no matching record is found for the given symbol
                or synonym.
            MultipleResultsFound: If multiple records are found for the given
                symbol or synonym.
        """
        if case_insensitive:
            where_clause = func.lower(Gene.symbol) == id.lower()
        else:
            where_clause = Gene.symbol == id

        stmt = select(Gene).where(where_clause)
        result = await session.execute(stmt)
        rows = result.scalars().all()

        if len(rows) > 1:
            raise MultipleResultsFound(
                f"Multiple records found for symbol '{id}' in {self.table_name()}"
            )
        if not rows:
            return await self.__resolve_synonyms(session, id, case_insensitive)

        record: Self = cast(Self, rows[0])
        return {"gene_id": record.gene_id, "ensembl_id": record.ensembl_id}

    async def __resolve_gene_xref(
        self, session: AsyncSession, id: str, gene_identifier_type: GeneXRefType
    ):
        stmt = select(Gene).where(Gene.xrefs[str(gene_identifier_type)].astext == id)
        result = await session.execute(stmt)
        rows = result.scalars().all()
        if not rows:
            raise NoResultFound(
                f"No record for {{{str(gene_identifier_type)}:{id}}} found in {self.table_name()}"
            )
        if len(rows) > 1:
            raise MultipleResultsFound(
                f"Multiple records found for {{{str(gene_identifier_type)}:{id}}} found in {self.table_name()}"
            )
        record: Self = cast(Self, rows[0])
        return {"gene_id": record.gene_id, "ensembl_id": record.ensembl_id}

    async def resolve_identifier(
        self,
        session: AsyncSession,
        id: str,
        gene_identifier_type: GeneXRefType,
        case_insensitive: bool = False,
    ):
        """
        Resolve a gene record by a given identifier and identifier type.

        Supports lookup by Ensembl ID, gene symbol (not implemented), or any
        external ID stored in the external_ids JSONB column.

        Args:
            id (str): The identifier value to resolve (e.g., Ensembl ID,
                HGNC ID).
            gene_identifier_type (GeneXRefType): The type of identifier
                to use for lookup.  If "None" will search
            session (AsyncSession): SQLAlchemy async session for database
                access.

        Returns:
            dict: Dictionary containing the primary key (gene_id) and
                stable identifier (ensembl_id) for the resolved gene record.

        Raises:
            NoResultFound: If no matching record is found for the given
                identifier.
            MultipleResultsFound: If multiple records are found for the given
                identifier.

        Example:
            await gene.resolve_identifier(
                "ENSG00000123456", GeneXRefType.ENSEMBL, session
            )
        """
        if gene_identifier_type == GeneXRefType.ENSEMBL:
            record: Gene = cast(
                Gene, await super().find_record(session, {"ensembl_id": id.upper()})
            )
            return {"gene_id": record.gene_id, "ensembl_id": record.ensembl_id}

        if gene_identifier_type == GeneXRefType.SYMBOL:
            return await self.resolve_gene_symobl(session, id, case_insensitive)

        else:  # check against the external_ids
            return await self.__resolve_gene_xref(session, id, gene_identifier_type)
