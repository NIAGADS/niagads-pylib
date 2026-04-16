"""
SQLAlchemy ORM table definitions for ontology term reference tables.

Enables foreign key references from other tables to ontology terms.
Intended for use alongside the ontology graph schema for comprehensive ontology support.
"""

from typing import Optional, Union
from uuid import uuid4

from niagads.common.reference.ontologies.types import EntityTypeIRI
from niagads.database.helpers import enum_column, enum_constraint
from niagads.database.genomicsdb.schema.mixins import IdAliasMixin
from niagads.database.genomicsdb.schema.reference.base import ReferenceTableBase
from niagads.database.genomicsdb.schema.reference.externaldb import ExternalDatabase
from niagads.database.genomicsdb.schema.reference.mixins import ExternalDatabaseMixin
from niagads.utils.string import jaccard_word_similarity
from pydantic import BaseModel, Field
from sqlalchemy import TEXT, Boolean, Index, String, UniqueConstraint, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.ext.hybrid import hybrid_property
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.exc import MultipleResultsFound, NoResultFound
from sqlalchemy.dialects.postgresql import ARRAY


class OntologyTerm(ReferenceTableBase, ExternalDatabaseMixin, IdAliasMixin):
    __tablename__ = "ontologyterm"
    __table_args__ = (
        *ExternalDatabaseMixin.__table_args__,
        UniqueConstraint("source_id", name="uq_ontology_term_id"),
        enum_constraint("entity_type", EntityTypeIRI, use_enum_names=True),
        Index(
            "ix_ontologyterm_term_trgm",
            "term",
            postgresql_using="gin",
            postgresql_ops={"term": "gin_trgm_ops"},
        ),
        ReferenceTableBase.__table_args__,
    )
    _stable_id = "source_id"

    ontology_term_id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    namespace: Mapped[str] = mapped_column(String(50), nullable=True, index=True)
    term: Mapped[str] = mapped_column(String(512), index=True, nullable=False)
    term_iri: Mapped[str] = mapped_column(String(250), index=False, nullable=False)
    entity_type: Mapped[str] = enum_column(EntityTypeIRI, use_enum_names=True)
    label: Mapped[str] = mapped_column(String(512), nullable=True)
    definition: Mapped[str] = mapped_column(TEXT, nullable=True)
    synonyms: Mapped[list[str]] = mapped_column(ARRAY(String(250)), nullable=True)
    is_deprecated: Mapped[bool] = mapped_column(Boolean, nullable=True)

    @hybrid_property
    def curie(self):
        return self.source_id

    @curie.expression
    def curie(cls):
        return cls.source_id

    # -------------------------
    # Term Lookups
    # -------------------------

    @classmethod
    async def find_primary_key(
        cls,
        session: AsyncSession,
        term: str = None,
        curie: str = None,
        external_database_id: int = None,
        search_synonyms: bool = False,
        allow_multiple: bool = False,
    ):
        """wrapper for TransactionTable `find_primary_key` that allows searching of synonyms"""
        filters: dict = {}
        if term is not None:
            filters["term"] = term
        if curie is not None:
            filters["source_id"] = curie
        if len(filters) == 0:
            raise ValueError(
                "Must provide at least one of `term` or `curie` to look up an ontology term"
            )

        if external_database_id is not None:
            filters["external_database_id"] = external_database_id

        if not search_synonyms:
            return await super().find_primary_key.__func__(
                cls, session, filters=filters
            )
        else:
            if term is None:
                raise ValueError("Can only match synonyms if a `term` is provided.")
            stmt = select(OntologyTerm.ontology_term_id).where(
                OntologyTerm.synonyms.contains([term])
            )
            result = await session.execute(stmt)
            rows = result.scalars().all()
            if not rows:
                raise NoResultFound(
                    f"No record found for {filters} in {cls.table_name()}"
                )
            if len(rows) > 1:
                if allow_multiple:
                    return rows
                else:
                    raise MultipleResultsFound(
                        f"Multiple records found for {filters} in {cls.table_name()}"
                    )
            return rows[0]

    @classmethod
    async def retrieve_term_pk_mapping(
        cls,
        session: AsyncSession,
        ontology_ref: Union[str, int],
        map_thru_term: bool = False,
    ):
        """Retrieve a mapping of Ensembl gene source IDs to primary key gene IDs.

        Args:
            session (AsyncSession): SQLAlchemy async session for database access.
            ontology_ref (str, int): Ontology reference.  Can be namespace (str) or external_database_id (int)
            map_thru_term (optional, bool): When True, map term (& synonyms) -> PK, When False map curie -> PK.  Defaults to False

        Returns:
            dict[str, int]: Mapping from lookup value to ontology_term_id (primary key).

        """

        if isinstance(ontology_ref, int):
            external_database_id: int = ontology_ref
        else:
            external_database_id: int = await ExternalDatabase.find_primary_key(
                session, filters={"database_key": ontology_ref}
            )

        mapping = {}
        if not map_thru_term:
            stmt = select(OntologyTerm.ontology_term_id, OntologyTerm.curie).where(
                OntologyTerm.external_database_id == external_database_id
            )
            records = (await session.execute(stmt)).all()
            for ontology_term_id, curie in records:
                mapping[curie] = ontology_term_id
        else:
            # also need to do labels and synonyms
            stmt = select(
                OntologyTerm.ontology_term_id,
                OntologyTerm.term,
                OntologyTerm.synonyms,
            ).where(OntologyTerm.external_database_id == external_database_id)
            records = (await session.execute(stmt)).all()

            # FIXME - raise an error?
            for ontology_term_id, term, synonyms in records:
                mapping[term] = ontology_term_id

                # these may introduce duplicates
                # give term priority
                if synonyms is not None:
                    for syn in synonyms:
                        if syn in mapping:
                            continue
                        mapping[syn] = ontology_term_id

        return mapping

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
            ontology: ExternalDatabase = await ExternalDatabase.fetch_record(
                session, {"external_database_id": self.external_database_id}
            )
            return ontology.database_key == namespace

    async def _update_definition(self, session: AsyncSession, definition: str) -> bool:
        self.definition = definition
        await self.update(session)
        return True

    async def resolve_synonyms(
        self, session: AsyncSession, new_synonyms: list[str]
    ) -> bool:
        """
        Merge new synonyms with existing synonyms, removing duplicates.

        Args:
            session (AsyncSession): SQLAlchemy async session.
            new_synonyms (list[str]): New synonym strings to merge.

        Returns:
            bool: True if synonyms were updated, False if new_synonyms was empty.
        """
        if not new_synonyms:
            return False
        if not self.synonyms:
            self.synonyms = sorted(new_synonyms)
        else:
            self.synonyms = sorted(list(set(self.synonyms) | set(new_synonyms)))

        await self.update(session)
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
        if not new_definition:
            return False

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
