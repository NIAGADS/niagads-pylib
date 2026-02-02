"""
SQLAlchemy ORM table definitions for ontology term reference tables.

Enables foreign key references from other tables to ontology terms.
Intended for use alongside the ontology graph schema for comprehensive ontology support.
"""

from typing import Optional
from uuid import uuid4

from niagads.common.constants.ontologies import EntityTypeIRI
from niagads.database.helpers import enum_column, enum_constraint
from niagads.database.mixins import EmbeddingMixin
from niagads.genomicsdb.schema.mixins import IdAliasMixin
from niagads.genomicsdb.schema.reference.base import ReferenceTableBase
from niagads.genomicsdb.schema.reference.externaldb import ExternalDatabase
from niagads.genomicsdb.schema.reference.mixins import ExternalDatabaseMixin
from niagads.utils.string import jaccard_word_similarity
from pydantic import BaseModel, Field
from sqlalchemy import ARRAY, TEXT, Boolean, Index, String, UniqueConstraint
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.ext.hybrid import hybrid_property
from sqlalchemy.orm import Mapped, mapped_column


class OntologyTerm(
    ReferenceTableBase, ExternalDatabaseMixin, EmbeddingMixin, IdAliasMixin
):
    __tablename__ = "ontologyterm"
    __table_args__ = (
        UniqueConstraint("source_id", name="uq_ontology_term_id"),
        enum_constraint("entity_type", EntityTypeIRI, use_enum_names=True),
        Index(
            "ix_ontologyterm_term_trgm",
            "term",
            postgresql_using="gin",
            postgresql_ops={"term": "gin_trgm_ops"},
        ),
    )
    _stable_id = "source_id"

    ontology_term_id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    term: Mapped[str] = mapped_column(String(512), index=True, nullable=False)
    term_iri: Mapped[str] = mapped_column(String(250), index=False, nullable=False)
    entity_type: Mapped[str] = enum_column(EntityTypeIRI, use_enum_names=True)
    label: Mapped[str] = mapped_column(String(100), nullable=True)
    definition: Mapped[str] = mapped_column(TEXT, nullable=True)
    synonyms: Mapped[list[str]] = mapped_column(ARRAY, nullable=True)
    is_deprecated: Mapped[bool] = mapped_column(Boolean, nullable=True)

    @hybrid_property
    def curie(self):
        return self.source_id

    @curie.expression
    def curie(cls):
        return cls.source_id

    # -------------------------
    # Duplicate Term Handlers
    # -------------------------

    async def in_namespace(self, session: AsyncSession, namespace: str) -> bool:
        """
        Check if this term's IRI starts with the given namespace.

        Args:
            namespace (str): The namespace to check; may be an ontology code

        Returns:
            bool: True if term_iri starts with namespace, else False.
        """
        if namespace.startswith("http"):
            return self.term_iri.startswith(namespace)
        else:  # assume namespace ==  ontology code
            ontology: ExternalDatabase = await ExternalDatabase.find_record(
                session, {"external_database_id": self.external_database_id}
            )
            return ontology.database_key == namespace

    async def _update_definition(self, session: AsyncSession, definition) -> bool:
        self.definition = definition
        await session.flush()
        return True

    async def resolve_definition(
        self, session: AsyncSession, new_definition: str, namespace: str
    ) -> bool:
        """
        Select the preferred definition for a duplicate ontology term.

        Prefers the new definition if it comes from the source ontology. Otherwise,
        selects the new definition if it is sufficiently different and longer.
        If only one definition is present, returns the new one.

        Args:
            new_definition (str): Candidate definition string.
            namespace (str): Source ontology namespace for the new definition.

        Returns:
            True if definition was updated.  False otherwise.
        """
        if not self.definition:
            return await self._update_definition(session, new_definition)

        # checking here to avoid the namespace lookup
        # unless necessary
        if new_definition == self.definition:
            return False  # no update needed

        # Prefer new if it comes from the source ontology for the term
        if await self.in_namespace(session, namespace):
            return await self._update_definition(session, new_definition)

        # otherwise, assume more comprehensive definition is correct
        similarity = jaccard_word_similarity(new_definition, self.definition)
        is_longer = len(new_definition) > len(self.definition)
        if similarity < 0.5 and is_longer:
            return await self._update_definition(session, new_definition)

        # Otherwise, keep existing
        return False


# Pydantic model wrappers w/database operations for graph objects
# Note: ontology_id / run_id will be required for database submits, but are
# set to optional because in the ETL they are not known at initialization
class OntologyGraphTermVertex(BaseModel):
    """
    AGE :term vertex model.
    Represents a deduplicated ontology term with core properties.
    """

    ontology_term_id: int = Field(..., description="primary key field")
    term_iri: str = Field(
        ..., description="Full URI (e.g., http://purl.obolibrary.org/obo/GO_0006915)"
    )
    curie: Optional[str] = Field(None, description="CURIE form (e.g., GO:0006915)")
    term: Optional[str] = Field(None, description="Term name/label")
    label: Optional[str] = Field(None, description="Display-friendly label")
    definition: Optional[str] = Field(None, description="Term definition")
    synonyms: Optional[list[str]] = Field(None, description="Array of synonym strings")
    entity_type: str = Field(None, description="ontology entity type")
    is_deprecated: bool = Field(False, description="Whether term is deprecated")

    run_id: Optional[int] = Field(
        None, description="References admin.etlrun for versioning"
    )

    # TODO
    async def submit(self, session: AsyncSession):
        raise NotImplementedError()

    async def exists(self, session: AsyncSession):
        raise NotImplementedError()


class OntologyGraphTriple(BaseModel):
    """
    AGE triple edge model.
    Represents a generic RDF triple (subject, predicate, object).
    Used for relationships not covered by named edge types and for annotation properties.
    """

    subject: OntologyGraphTermVertex = Field(..., description="Subject term")
    predicate: OntologyGraphTermVertex = Field(
        ..., description="Predicate term (CURIE)"
    )
    object: OntologyGraphTermVertex = Field(..., description="Object term")
    ontology_id: Optional[int] = Field(None, description="Source ontology")
    run_id: Optional[int] = Field(None, description="Version/load snapshot")

    # TODO
    async def submit(self, session: AsyncSession):
        raise NotImplementedError()

    async def exists(self, session: AsyncSession):
        raise NotImplementedError()

    async def is_valid(self, session: AsyncSession):
        await self.subject.exists()
        await self.predicate.exists()
        await self.object.exists()


class OntologyGraphOntologyVertex(BaseModel):
    """
    AGE :ontology vertex model.
    Represents ontology metadata and serves as target for defined_in edges.
    """

    ontology_id: int = Field(
        ..., description="References reference.externaldatabase (unique key)"
    )
    ontology: Optional[str] = Field(None, description="Ontology name")
    namespace: Optional[str] = Field(
        None, description="Ontology namespace or code for disambiguation"
    )
    version: Optional[str] = Field(None, description="Release/version identifier")
    run_id: Optional[int] = Field(None, description="References admin.etlrun")

    # TODO
    async def submit(self, session: AsyncSession):
        raise NotImplementedError()

    async def exists(self, session: AsyncSession):
        raise NotImplementedError()


class OntologyGraphRestrictionVertex(BaseModel):
    """
    AGE :restriction vertex model.
    Represents an anonymous blank node that serves as a container for OWL restriction properties.
    The restriction's definition is the subgraph of outbound edges from it.
    """

    restriction_id: str = Field(
        default_factory=lambda: str(uuid4()),
        description="Blank node identifier (UUID4)",
    )
    ontology_id: Optional[int] = Field(
        None, description="Source ontology (scopes the restriction)"
    )
    run_id: Optional[int] = Field(None, description="Version/load snapshot")

    # TODO
    async def submit(self, session: AsyncSession):
        raise NotImplementedError()
