"""
SQLAlchemy ORM table definitions for ontology term reference tables.

Enables foreign key references from other tables to ontology terms.
Intended for use alongside the ontology graph schema for comprehensive ontology support.
"""

from niagads.database.mixins.embeddings import EmbeddingMixin
from niagads.genomicsdb.schema.reference.base import ReferenceTableBase
from niagads.genomicsdb.schema.reference.mixins import ExternalDatabaseMixin
from sqlalchemy import ARRAY, TEXT, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column


class OntologyTerm(ReferenceTableBase, ExternalDatabaseMixin, EmbeddingMixin):
    __tablename__ = "ontologyterm"
    __table_args__ = (UniqueConstraint("source_id", name="uq_ontology_term_id"),)
    stable_id = "source_id"

    ontology_term_id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    term: Mapped[str] = mapped_column(String(512), index=True, nullable=False)
    label: Mapped[str] = mapped_column(String(100), nullable=True)
    description: Mapped[str] = mapped_column(TEXT, nullable=True)
    synonyms: Mapped[list[str]] = mapped_column(ARRAY, nullable=True)
