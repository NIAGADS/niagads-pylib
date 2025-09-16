"""`Gene` database model"""

from typing import Any, Optional

from niagads.assembly.core import Human
from niagads.common.models.composite_attributes.gene import (
    GOAnnotation,
    PathwayAnnotation,
)
from niagads.database.core import ModelDumpMixin, enum_constraint
from niagads.database.genomicsdb.schemas.gene.base import GeneSchemaBase
from niagads.utils.regular_expressions import RegularExpressions
from sqlalchemy import Column, Enum, Index
from sqlalchemy.dialects.postgresql import INT4RANGE, JSONB
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.schema import CheckConstraint
from sqlalchemy_utils import LtreeType


class Documents(ModelDumpMixin, GeneSchemaBase):
    __tablename__ = "documents"
    __table_args__ = (
        enum_constraint("shard_chromosome", Human),
        CheckConstraint(
            f"ensembl_id ~ '{RegularExpressions.ENSEMBL_GENE_ID}'",
            name="ensembl_id_format_check",
        ),
        Index("ix_gene_location", "location", postgresql_using="gist"),
        Index("ix_gene_bin_index", "bin_index", postgresql_using="gist"),
    )

    gene_id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    ensembl_id: Mapped[str] = mapped_column(uniuqe=True, index=True)
    chromosome: str = Column(Enum(Human, native_enum=False))
    bin_index: Mapped[str] = mapped_column(LtreeType)
    location: Mapped[Any] = mapped_column(INT4RANGE)
    go_annotation: Mapped[Optional[GOAnnotation]] = mapped_column(
        JSONB(none_as_null=True)
    )
    pathway_membership: Mapped[Optional[PathwayAnnotation]]
