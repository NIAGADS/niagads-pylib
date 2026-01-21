"""
SQLAlchemy ORM table definitions for gene annotation and membership tables.

Defines annotation, pathway membership, and related tables for gene-centric knowledge in the genomicsdb gene schema.
"""

from niagads.genomicsdb.schema.gene.base import GeneTableBase, gene_fk_column

from sqlalchemy import ForeignKey, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column


class PathwayMembership(GeneTableBase):
    __tablename__ = "pathwaymembership"
    __table_args__ = (
        UniqueConstraint("pathway_id", "gene_id", name="uq_pathway_gene_membership"),
    )
    stable_id = None

    pathway_membership_id: Mapped[int] = mapped_column(
        primary_key=True, autoincrement=True
    )
    pathway_id: Mapped[int] = mapped_column(
        ForeignKey("reference.pathway.pathway_id"),
        nullable=False,
        index=True,
    )
    gene_id: Mapped[int] = gene_fk_column()
    # evidence: -> ontology_term graph link
