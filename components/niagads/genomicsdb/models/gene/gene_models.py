"""`Gene` database model"""

from typing import Any

from niagads.assembly.core import Human
from niagads.database import enum_constraint
from niagads.database.mixins.ranges import GenomicRegionMixin
from niagads.genomicsdb.models.gene.base import GeneSchemaBase
from niagads.utils.regular_expressions import RegularExpressions
from sqlalchemy import Index, String
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.schema import CheckConstraint


class Gene(GeneSchemaBase, GenomicRegionMixin):
    __tablename__ = "models"
    __table_args__ = (
        enum_constraint("shard_chromosome", Human),
        CheckConstraint(
            f"ensembl_id ~ '{RegularExpressions.ENSEMBL_GENE_ID}'",
            name="ensembl_id_format_check",
        ),
        Index("ix_gene_location", "location", postgresql_using="gist"),
    )

    gene_id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    ensembl_id: Mapped[str] = mapped_column(uniuqe=True, index=True)
    gene_type: Mapped[str] = mapped_column(String(150))
    name: Mapped[str] = mapped_column(String(250))
    cytogenic_location: str
    external_ids: Mapped[dict] = mapped_column(JSONB, nullable=True)
