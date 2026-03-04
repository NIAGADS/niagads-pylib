"""
SQLAlchemy ORM table definitions for core gene structure entities: gene, transcript, and exon.

Defines the canonical tables for gene structure in the genomicsdb gene schema.
"""

from niagads.database.mixins import GenomicRegionMixin
from niagads.genomicsdb.schema.gene.base import GeneTableBase
from niagads.genomicsdb.schema.gene.helpers import gene_fk_column
from niagads.genomicsdb.schema.mixins import IdAliasMixin
from niagads.utils.regular_expressions import RegularExpressions
from sqlalchemy import ForeignKey, String
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.schema import CheckConstraint


# Note: no IdAliasMixin on this one b/c API, etc will query the RAG Doc view
class GeneModel(GeneTableBase, GenomicRegionMixin, IdAliasMixin):
    __tablename__ = "gene"
    __table_args__ = (
        *GenomicRegionMixin.__table_args__,
        *GenomicRegionMixin.get_indexes(GeneTableBase._schema, __tablename__),
        CheckConstraint(
            f"ensembl_id ~ '{RegularExpressions.ENSEMBL_GENE_ID}'",
            name="ensembl_gene_id_format_check",
        ),
        GeneTableBase.__table_args__,
    )

    gene_id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    gene_symbol: Mapped[str] = mapped_column(String(50))
    gene_name: Mapped[str] = mapped_column(String(250))
    gene_type: Mapped[str] = mapped_column(String(150))  # TODO: map to ontology term?


class TranscriptModel(GeneTableBase, GenomicRegionMixin, IdAliasMixin):
    __tablename__ = "transcript"
    __table_args__ = (
        *GenomicRegionMixin.__table_args__,
        *GenomicRegionMixin.get_indexes(GeneTableBase._schema, __tablename__),
        CheckConstraint(
            f"ensembl_id ~ '{RegularExpressions.ENSEMBL_TRANSCRIPT_ID}'",
            name="ensembl_transcript_id_format_check",
        ),
        GeneTableBase.__table_args__,
    )

    transcript_id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    gene_id: Mapped[int] = gene_fk_column()


class ExonModel(GeneTableBase, GenomicRegionMixin, IdAliasMixin):
    __tablename__ = "exon"
    __table_args__ = (
        *GenomicRegionMixin.__table_args__,
        *GenomicRegionMixin.get_indexes(GeneTableBase._schema, __tablename__),
        CheckConstraint(
            f"ensembl_id ~ '{RegularExpressions.ENSEMBL_EXON_ID}'",
            name="ensembl_exon_id_format_check",
        ),
        GeneTableBase.__table_args__,
    )

    exon_id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    gene_id: Mapped[int] = gene_fk_column()  # type: ignore
    transcript_id: Mapped[int] = mapped_column(
        ForeignKey("gene.transcript.transcript_id"), index=True, nullable=False
    )
