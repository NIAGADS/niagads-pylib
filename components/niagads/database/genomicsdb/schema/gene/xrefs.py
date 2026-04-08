from enum import auto
from typing import Optional

from niagads.database.genomicsdb.schema.gene.base import GeneTableBase
from niagads.database.genomicsdb.schema.gene.helpers import gene_fk_column
from niagads.database.genomicsdb.schema.gene.structure import GeneModel
from niagads.database.genomicsdb.schema.reference.helpers import ontology_term_fk_column
from niagads.database.genomicsdb.schema.reference.mixins import ExternalDatabaseMixin
from niagads.database.helpers import enum_column, enum_constraint
from niagads.enums.core import CaseInsensitiveEnum
from sqlalchemy import String, and_, func, select
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.exc import NoResultFound, MultipleResultsFound


class GeneIdentifierType(CaseInsensitiveEnum):
    ENSEMBL = "ensembl_id"
    ENTREZ = "entrez_id"
    NCBI = "entrez_id"
    SYMBOL = "gene_symbol"
    HGNC = "hgnc_id"
    UNIPROT = "uniprot_id"
    OMIM = "omim_id"
    UCSC = "ucsc_id"
    REFSEQ = "refseq_id"


class GeneXRefCategory(CaseInsensitiveEnum):
    IDENTIFIER = auto()
    NOMENCLATURE = auto()
    LOCUS = auto()
    PUBLICATION = auto()
    RESOURCE_LINK = auto()
    CLASSIFICATION = auto()
    GROUP_MEMBERSHIP = auto()
    ORTHOLOG = auto()


# don't want the external_database_id/source_id constraint as they will be repeated
# that is why source_id is not a stable_id
class GeneXRef(GeneTableBase, ExternalDatabaseMixin):
    __tablename__ = "xref"
    __table_args__ = (
        enum_constraint("xref_category", GeneXRefCategory),
        GeneTableBase.__table_args__,
    )
    _stable_id = None
    xref_id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    gene_id: Mapped[int] = gene_fk_column()
    xref_category: Mapped[GeneXRefCategory] = enum_column(
        GeneXRefCategory, index=True, nullable=False
    )
    xref_label: Mapped[Optional[str]] = mapped_column(
        String(50), index=True, nullable=True
    )
    xref_value: Mapped[Optional[str]] = mapped_column(
        String(250), index=True, nullable=True
    )

    ontology_term_id: Mapped[Optional[int]] = ontology_term_fk_column(
        nullable=True, index=True
    )
    cross_references: Mapped[Optional[dict]] = mapped_column(
        JSONB(none_as_null=True), nullable=True
    )

    @classmethod
    async def resolve_symbol(
        cls,
        session: AsyncSession,
        symbol: str,
        match_synonyms: bool = False,
        allow_multiple: bool = False,
    ):
        """
        Resolve a gene record by its symbol using case insensitive matching,
        with optional matching against synonyms

        To enforce case-sensitive matching to official Gene Symbols,
        please use the `resolve_identifier` function

        Args:
            session (AsyncSession): SQLAlchemy async session for database
                access.
            id (str): The gene symbol to resolve.
            match_synonyms (bool, optional): If True, match against synonyms if
                match to symbol is not found. Defaults to False.
            allow_multiple (Optional, bool): flag indicating whether to
                fail on multiple matches.  Defaults to False.

        Returns:
            record, list[int]: the primary key for the gene record (or list of primary keys if `allow_multiple`)

        Raises:
            NoResultFound: If no matching record is found for the given symbol
                or synonym.
            MultipleResultsFound: If multiple records are found for the given
                symbol or synonym.
        """
        SYNONYM_FIELDS = ["alias_symbol", "prev_symbol"]

        stmt = select(GeneModel.gene_id).where(
            func.lower(symbol) == GeneModel.gene_symbol
        )
        result = await session.execute(stmt)
        records = result.scalars().all()
        if records:
            if len(records) > 1:
                if allow_multiple:
                    return records
                else:
                    raise MultipleResultsFound(
                        f"Multiple gene records found matching symbol - {symbol}: {records}"
                    )
            else:
                return records[0]

        if match_synonyms:
            stmt = select(GeneXRef.gene_id).where(
                and_(
                    func.lower(symbol) == GeneXRef.xref_value,
                    GeneXRef.xref_label.in_(SYNONYM_FIELDS),
                )
            )
            result = await session.execute(stmt)
            records = result.scalars().all()

            if not records:
                raise NoResultFound(
                    f"No matching genes found for symbol (or synonym): {symbol}"
                )
            if len(records) > 1:
                if allow_multiple:
                    return records
                else:
                    raise MultipleResultsFound(
                        f"Multiple gene records found matching symbol - {symbol}: {records}"
                    )
            else:  # one match
                return records[0]

        else:  # if not matching against synonyms
            raise NoResultFound(f"No matching genes found for symbol: {symbol}")

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
                synonyms).  Defaults to  True.
            allow_multiple (Optional, bool): flag indicating whether to fail on multiple matches
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
        if gene_identifier_type == GeneIdentifierType.ENSEMBL:
            return await GeneModel.find_primary_key(
                session, {"source_id": id.upper()}, allow_multiple=allow_multiple
            )
        elif gene_identifier_type == GeneIdentifierType.SYMBOL:
            if require_exact_match:
                return await GeneModel.find_primary_key(
                    session, {"gene_symbol", id}, allow_multiple=allow_multiple
                )
            else:
                return await cls.resolve_symbol(
                    session, id, require_exact_match, allow_multiple
                )

        else:  # check against the external_ids
            return await cls.find_primary_key(
                session,
                filters={"xref_label": str(gene_identifier_type), "xref_value": id},
                allow_multiple=allow_multiple,
            )
