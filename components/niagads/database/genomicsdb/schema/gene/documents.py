"""
Materialized view and document-oriented ORM definitions for gene-centric RAG (Retrieval-Augmented Generation) documents.

Defines the RAG document materialized view and related fields for querying gene knowledge in the genomicsdb gene schema.
"""

from typing import Optional

from niagads.common.gene.models.annotation import (
    GOAssociation,
    PathwayMembership,
)
from niagads.database.genomicsdb.schema.gene.structure import GeneModel
from niagads.database.mixins import GenomicRegionMixin
from niagads.database.genomicsdb.schema.gene.base import GeneMaterializedViewBase
from niagads.database.genomicsdb.schema.gene.xrefs import GeneIdentifierType, GeneXRef
from niagads.database.genomicsdb.schema.mixins import IdAliasMixin
from sqlalchemy import ARRAY, String
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import Mapped, mapped_column


class Gene(GeneMaterializedViewBase, GenomicRegionMixin, IdAliasMixin):
    __tablename__ = "document_mv"

    __table_args__ = (
        *GenomicRegionMixin.get_indexes(
            GeneMaterializedViewBase._schema, __tablename__
        ),
        GeneMaterializedViewBase.__table_args__,
    )

    gene_id: Mapped[int] = mapped_column(index=True, primary_key=True)  # not PK b/c MV
    ensembl_id: Mapped[str] = mapped_column(unique=True, index=True)
    symbol: Mapped[str] = mapped_column(String(50))
    name: Mapped[str] = mapped_column(String(250))
    gene_type: Mapped[str] = mapped_column(String(150))
    synonyms: Mapped[list[str]] = mapped_column(ARRAY(String), nullable=True)
    cytogenic_location: Mapped[str] = mapped_column(String(100), index=True)
    xrefs: Mapped[dict] = mapped_column(JSONB)
    go_annotation: Mapped[Optional[GOAssociation]] = mapped_column(
        JSONB(none_as_null=True)
    )
    pathway_membership: Mapped[Optional[PathwayMembership]] = mapped_column(
        JSONB(none_as_null=True)
    )
    data_sources: Mapped[dict] = mapped_column(JSONB(none_as_null=True))

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
                session, {"gene_symbol", id}, allow_multiple=allow_multiple
            )

        else:  # ditto
            return await GeneXRef.resolve_identifier(
                session,
                id,
                gene_identifier_type,
                require_exact_match=require_exact_match,
                allow_multiple=allow_multiple,
            )
