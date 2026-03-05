"""
SQLAlchemy ORM table definitions for gene annotation and membership tables.

Defines annotation, pathway membership, and related tables for gene-centric knowledge in the genomicsdb gene schema.
"""

from niagads.genomicsdb.schema.admin.mixins import TableRefMixin
from niagads.genomicsdb.schema.gene.base import GeneTableBase
from niagads.genomicsdb.schema.gene.helpers import gene_fk_column
from niagads.genomicsdb.schema.reference.helpers import ontology_term_fk_column
from sqlalchemy import ForeignKey, UniqueConstraint
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column


class PathwayMembership(GeneTableBase):
    __tablename__ = "pathwaymembership"
    __table_args__ = (
        UniqueConstraint("pathway_id", "gene_id", name="uq_pathway_gene_membership"),
        GeneTableBase.__table_args__,
    )
    _stable_id = None

    pathway_membership_id: Mapped[int] = mapped_column(
        primary_key=True, autoincrement=True
    )
    pathway_id: Mapped[int] = mapped_column(
        ForeignKey("reference.pathway.pathway_id"),
        nullable=False,
        index=True,
    )
    gene_id: Mapped[int] = gene_fk_column()


class GOAssociation(GeneTableBase):
    __tablename__ = "goassociation"
    __table_args__ = (
        UniqueConstraint("go_term_id", "gene_id", name="uq_go_association"),
        GeneTableBase.__table_args__,
    )
    _stable_id = None

    go_association_id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    go_term_id: Mapped[int] = ontology_term_fk_column()
    gene_id: Mapped[int] = gene_fk_column()


class AnnotationEvidence(GeneTableBase, TableRefMixin):
    __tablename__ = "annotationevidence"
    __table_args__ = (
        UniqueConstraint(
            "evidence_code_id", "table_id", "row_id", name="uq_gene_annotation_evidence"
        ),
        GeneTableBase.__table_args__,
    )
    _stable_id = None
    annotation_evidence_id: Mapped[int] = mapped_column(
        primary_key=True, autoincrement=True
    )
    evidence_code_id: Mapped[int] = ontology_term_fk_column()
    qualifiers: Mapped[dict] = mapped_column(JSONB(none_as_null=True))
