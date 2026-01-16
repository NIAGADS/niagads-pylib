"""`Gene` database model"""

from typing import Self, cast
from niagads.database.mixins.ranges import GenomicRegionMixin
from niagads.enums.core import CaseInsensitiveEnum
from niagads.genomicsdb.schema.gene.base import GeneSchemaBase
from niagads.utils.regular_expressions import RegularExpressions
from sqlalchemy import String, select
from sqlalchemy.dialects.postgresql import JSONB, ARRAY
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy import ForeignKey
from sqlalchemy.schema import CheckConstraint
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.exc import MultipleResultsFound, NoResultFound

# TODO: external db refs -> how to handle multiple data sources for the info in a table? array? or two fields


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
    # TODO: orthologs?


class Gene(GeneSchemaBase, GenomicRegionMixin):
    __tablename__ = "gene"
    __table_args__ = (
        CheckConstraint(
            f"ensembl_id ~ '{RegularExpressions.ENSEMBL_GENE_ID}'",
            name="ensembl_id_format_check",
        ),
    )

    gene_id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    ensembl_id: Mapped[str] = mapped_column(uniuqe=True, index=True)
    symbol: Mapped[str] = mapped_column(String(50))
    name: Mapped[str] = mapped_column(String(250))
    gene_type: Mapped[str] = mapped_column(String(150))
    synonyms: Mapped[list[str]] = mapped_column(ARRAY(String), nullable=True)
    cytogenic_location: str = mapped_column(String(100), index=True)
    external_ids: Mapped[dict] = mapped_column(JSONB, nullable=True)
    # model_data_source: Mapped[int]
    # nomenclature_data_source: Mapped[int]
    # external_database_id: Mapped[list]

    async def resolve_identifier(
        self, id: str, gene_identifier_type: GeneIdentifierType, session: AsyncSession
    ):
        """
        Resolve a gene record by a given identifier and identifier type.

        Supports lookup by Ensembl ID, gene symbol (not implemented), or any
        external ID stored in the external_ids JSONB column.

        Args:
            id (str): The identifier value to resolve (e.g., Ensembl ID,
                HGNC ID).
            gene_identifier_type (GeneIdentifierType): The type of identifier
                to use for lookup.
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
            NotImplementedError: If lookup by gene symbol or synonyms is
                requested (not yet implemented).

        Example:
            await gene.resolve_identifier(
                "ENSG00000123456", GeneIdentifierType.ENSEMBL, session
            )
        """
        if gene_identifier_type == GeneIdentifierType.ENSEMBL:
            record: Self = cast(
                Self, await super().find_record({"ensembl_id": id.upper()})
            )
            return {"gene_id": record.gene_id, "ensembl_id": record.ensembl_id}
        if gene_identifier_type == GeneIdentifierType.SYMBOL:
            raise NotImplementedError(
                "need to write sql function to do case insensitive(?) match on symbol and synonyms"
            )
        else:  # check against the external_ids
            stmt = select(Gene).where(
                Gene.external_ids[str(gene_identifier_type)].astext == id
            )
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


class Transcript(GeneSchemaBase, GenomicRegionMixin):
    __tablename__ = "transcript"
    __table_args__ = (
        CheckConstraint(
            f"ensembl_id ~ '{RegularExpressions.ENSEMBL_TRANSCRIPT_ID}'",
            name="ensembl_id_format_check",
        ),
    )

    transcript_id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    ensembl_id: Mapped[str] = mapped_column(uniuqe=True, index=True)
    gene_id: Mapped[int] = mapped_column(ForeignKey("gene.model.gene_id"), index=True)


class Exon(GeneSchemaBase, GenomicRegionMixin):
    __tablename__ = "exon"
    __table_args__ = (
        CheckConstraint(
            f"ensembl_id ~ '{RegularExpressions.ENSEMBL_EXON_ID}'",
            name="ensembl_id_format_check",
        ),
    )

    exon_id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    ensembl_id: Mapped[str] = mapped_column(uniuqe=True, index=True)
    gene_id: Mapped[int] = mapped_column(ForeignKey("gene.model.gene_id"), index=True)
    transcript_id: Mapped[int] = mapped_column(
        ForeignKey("gene.model.transcript_id"), index=True
    )
