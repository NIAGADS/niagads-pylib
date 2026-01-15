"""`Gene` database model"""

from niagads.database.mixins.ranges import GenomicRegionMixin
from niagads.genomicsdb.schema.gene.base import GeneSchemaBase
from niagads.utils.regular_expressions import RegularExpressions
from sqlalchemy import String
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy import ForeignKey
from sqlalchemy.schema import CheckConstraint


class Gene(GeneSchemaBase, GenomicRegionMixin):
    __tablename__ = "model"
    __table_args__ = (
        CheckConstraint(
            f"ensembl_id ~ '{RegularExpressions.ENSEMBL_GENE_ID}'",
            name="ensembl_id_format_check",
        ),
    )

    gene_id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    ensembl_id: Mapped[str] = mapped_column(uniuqe=True, index=True)
    gene_type: Mapped[str] = mapped_column(String(150))
    name: Mapped[str] = mapped_column(String(250))
    cytogenic_location: str = mapped_column(String(100), index=True)
    external_ids: Mapped[dict] = mapped_column(JSONB, nullable=True)


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
