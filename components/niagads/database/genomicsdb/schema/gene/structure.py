"""
SQLAlchemy ORM table definitions for core gene structure entities: gene, transcript, and exon.

Defines the canonical tables for gene structure in the genomicsdb gene schema.
"""

from typing import Optional

from niagads.database.genomicsdb.schema.gene.base import GeneTableBase
from niagads.database.genomicsdb.schema.gene.helpers import gene_fk_column
from niagads.database.genomicsdb.schema.mixins import IdAliasMixin
from niagads.database.genomicsdb.schema.reference.helpers import ontology_term_fk_column
from niagads.database.mixins import GenomicRegionMixin
from niagads.utils.regular_expressions import RegularExpressions
from sqlalchemy import ForeignKey, Integer, String, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.schema import CheckConstraint


# Note: no IdAliasMixin on this one b/c API, etc will query the RAG Doc view
class GeneModel(GeneTableBase, GenomicRegionMixin, IdAliasMixin):
    __tablename__ = "gene"
    __table_args__ = (
        *GenomicRegionMixin.__table_args__,
        *GenomicRegionMixin.get_indexes(GeneTableBase._schema, __tablename__),
        *GenomicRegionMixin.set_bin_index_fk(GeneTableBase._schema, __tablename__),
        CheckConstraint(
            f"source_id ~ '{RegularExpressions.ENSEMBL_GENE_ID}'",
            name="gene_source_id_format_check",
        ),
        GeneTableBase.__table_args__,
    )

    gene_id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    gene_symbol: Mapped[str] = mapped_column(String(50))
    gene_name: Mapped[str] = mapped_column(String(500))
    gene_type_id: Mapped[int] = ontology_term_fk_column()  # TODO: map to ontology term?

    @classmethod
    async def retrieve_gene_pk_mapping(cls, session: AsyncSession):
        """Retrieve a mapping of Ensembl gene source IDs to primary key gene IDs.

        Args:
            session (AsyncSession): SQLAlchemy async session for database access.

        Returns:
            dict[str, int]: Mapping from Ensembl gene source_id to gene_id (primary key).

        """
        mapping = {}
        stmt = select(GeneModel.gene_id, GeneModel.source_id)
        records = (await session.execute(stmt)).mappings().all()
        for r in records:
            mapping[r["source_id"]] = r["gene_id"]
        return mapping


class TranscriptModel(GeneTableBase, GenomicRegionMixin, IdAliasMixin):
    __tablename__ = "transcript"
    __table_args__ = (
        *GenomicRegionMixin.__table_args__,
        *GenomicRegionMixin.get_indexes(GeneTableBase._schema, __tablename__),
        *GenomicRegionMixin.set_bin_index_fk(GeneTableBase._schema, __tablename__),
        CheckConstraint(
            f"source_id ~ '{RegularExpressions.ENSEMBL_TRANSCRIPT_ID}'",
            name="transcript_source_id_format_check",
        ),
        GeneTableBase.__table_args__,
    )

    transcript_id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String(50), nullable=True, index=True)
    gene_id: Mapped[int] = gene_fk_column()
    is_canonical: Mapped[bool] = mapped_column(index=True, nullable=True)


class ExonModel(GeneTableBase, GenomicRegionMixin, IdAliasMixin):
    __tablename__ = "exon"
    __table_args__ = (
        *GenomicRegionMixin.__table_args__,
        *GenomicRegionMixin.get_indexes(GeneTableBase._schema, __tablename__),
        *GenomicRegionMixin.set_bin_index_fk(GeneTableBase._schema, __tablename__),
        CheckConstraint(
            f"source_id ~ '{RegularExpressions.ENSEMBL_EXON_ID}'",
            name="exon_source_id_format_check",
        ),
        GeneTableBase.__table_args__,
    )

    exon_id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    gene_id: Mapped[int] = gene_fk_column()  # type: ignore
    transcript_id: Mapped[int] = mapped_column(
        ForeignKey("gene.transcript.transcript_id"), index=True, nullable=False
    )
    rank: Mapped[Optional[int]] = mapped_column(Integer, index=False, nullable=False)
