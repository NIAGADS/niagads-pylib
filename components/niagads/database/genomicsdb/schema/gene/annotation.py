"""
SQLAlchemy ORM table definitions for gene annotation and membership tables.

Defines annotation, pathway membership, and related tables for gene-centric knowledge in the genomicsdb gene schema.
"""

from niagads.common.models.annotations import AnnotationType
from niagads.database.genomicsdb.schema.admin.mixins import TableRefMixin
from niagads.database.genomicsdb.schema.base import GenomicsDBSchemaBase
from niagads.database.genomicsdb.schema.gene.base import GeneTableBase
from niagads.database.genomicsdb.schema.gene.helpers import gene_fk_column
from niagads.database.genomicsdb.schema.mixins import GenomicsDBTableMixin
from niagads.database.genomicsdb.schema.reference.helpers import ontology_term_fk_column
from sqlalchemy import ForeignKey, UniqueConstraint
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.ext.hybrid import hybrid_property


# these only need an external_database_id, but not a source_id
class AnnotationTableBase(GenomicsDBSchemaBase, GenomicsDBTableMixin):
    __abstract__ = True
    _stable_id = None
    _schema = "gene"

    __table_args__ = {"schema": _schema}

    external_database_id: Mapped[int] = mapped_column(
        ForeignKey("reference.externaldatabase.external_database_id"),
        nullable=False,
        index=True,
    )


class PathwayMembership(AnnotationTableBase):
    __tablename__ = "pathwaymembership"
    __table_args__ = (
        UniqueConstraint("pathway_id", "gene_id", name="uq_pathway_gene_membership"),
        GeneTableBase.__table_args__,
    )

    pathway_membership_id: Mapped[int] = mapped_column(
        primary_key=True, autoincrement=True
    )

    pathway_id: Mapped[int] = mapped_column(
        ForeignKey("reference.pathway.pathway_id"),
        nullable=False,
        index=True,
    )
    gene_id: Mapped[int] = gene_fk_column()

    @hybrid_property
    def annotation_type(self):
        return AnnotationType.SET

    @annotation_type.expression
    def annotation_type(cls):
        return AnnotationType.SET.name


class GOAssociation(AnnotationTableBase):
    __tablename__ = "goassociation"
    __table_args__ = (
        UniqueConstraint("go_term_id", "gene_id", name="uq_go_association"),
        GeneTableBase.__table_args__,
    )

    go_association_id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    go_term_id: Mapped[int] = ontology_term_fk_column()
    gene_id: Mapped[int] = gene_fk_column()

    @hybrid_property
    def annotation_type(self):
        return AnnotationType.KNOW

    @annotation_type.expression
    def annotation_type(cls):
        return AnnotationType.KNOW.name


class AnnotationEvidence(AnnotationTableBase, TableRefMixin):
    __tablename__ = "annotationevidence"
    __table_args__ = (
        UniqueConstraint(
            "evidence_code_id",
            "table_id",
            "row_id",
            "qualifiers",
            name="uq_gene_annotation_evidence",
        ),
        GeneTableBase.__table_args__,
    )

    annotation_evidence_id: Mapped[int] = mapped_column(
        primary_key=True, autoincrement=True
    )
    evidence_code_id: Mapped[int] = ontology_term_fk_column()
    qualifiers: Mapped[dict] = mapped_column(JSONB(none_as_null=True))
