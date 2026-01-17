"""
SQLAlchemy ORM table definitions for core gene structure entities: gene, transcript, and exon.

Defines the canonical tables for gene structure in the genomicsdb gene schema.
"""

from typing import Self, cast
from niagads.database.mixins.ranges import GenomicRegionMixin
from niagads.genomicsdb.schema.gene.base import GeneTableBase, gene_fk_column
from niagads.genomicsdb.schema.gene.xrefs import GeneIdentifierType
from niagads.genomicsdb.schema.reference.mixins import ExternalDatabaseMixin
from niagads.utils.regular_expressions import RegularExpressions
from sqlalchemy import String, select

from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy import ForeignKey
from sqlalchemy.schema import CheckConstraint


class GeneModel(GeneTableBase, GenomicRegionMixin, ExternalDatabaseMixin):
    __tablename__ = "gene"
    __table_args__ = (
        CheckConstraint(
            f"source_id ~ '{RegularExpressions.ENSEMBL_GENE_ID}'",
            name="ensembl_gene_id_format_check",
        ),
    )

    gene_id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    gene_symbol: Mapped[str] = mapped_column(String(50))
    gene_name: Mapped[str] = mapped_column(String(250))
    gene_type: Mapped[str] = mapped_column(String(150))


class TranscriptModel(GeneTableBase, GenomicRegionMixin, ExternalDatabaseMixin):
    __tablename__ = "transcript"
    __table_args__ = (
        CheckConstraint(
            f"source_id ~ '{RegularExpressions.ENSEMBL_TRANSCRIPT_ID}'",
            name="ensembl_transcript_id_format_check",
        ),
    )

    transcript_id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    gene_id: Mapped[int] = gene_fk_column()


class ExonModel(GeneTableBase, GenomicRegionMixin, ExternalDatabaseMixin):
    __tablename__ = "exon"
    __table_args__ = (
        CheckConstraint(
            f"source_id ~ '{RegularExpressions.ENSEMBL_EXON_ID}'",
            name="ensembl_exon_id_format_check",
        ),
    )

    exon_id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    gene_id: gene_fk_column()  # type: ignore
    transcript_id: Mapped[int] = mapped_column(
        ForeignKey("gene.transcript.transcript_id"), index=True, nullable=False
    )
