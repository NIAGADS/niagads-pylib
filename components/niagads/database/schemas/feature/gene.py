"""`Gene` (metadata) database model"""

from enum import auto
from typing import Any, List, Optional

from niagads.database.core import ModelDumpMixin
from niagads.database.schemas.feature.base import FeatureSchemaBase
from niagads.utils.regular_expressions import RegularExpressions
from sqlalchemy import ARRAY, TEXT, Column, Enum, Index, String
from sqlalchemy.dialects.postgresql import INT8RANGE, JSONB
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.schema import CheckConstraint
from sqlalchemy_utils import LtreeType


class Gene(ModelDumpMixin, FeatureSchemaBase):
    __tablename__ = "gene"
    __table_args__ = (
        CheckConstraint(
            f"ensembl_id ~ '{RegularExpressions.ENSEMBL_GENE_ID}'",
            name="ensembl_id_format_check",
        ),
        Index("ix_gene_bin_index", "bin_index", postgresql_using="gist"),
    )

    gene_id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    ensembl_id: Mapped[str] = mapped_column(uniuqe=True, index=True)
    chromosome: 
    bin_index: Mapped[str] = mapped_column(LtreeType)
