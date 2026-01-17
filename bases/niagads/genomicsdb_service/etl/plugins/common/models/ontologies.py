from niagads.common.models.ontology import OntologyTerm as __OntologyTerm
from niagads.common.models.ontology import OntologyTriple as __OntologyTriple
from niagads.enums.core import CaseInsensitiveEnum
from niagads.utils.string import jaccard_word_similarity
from pydantic import BaseModel
from sqlalchemy import text
from sqlalchemy.exc import NoResultFound


class RDFPropertyIRI(CaseInsensitiveEnum):
    """
    Enum for core RDF/OWL object property IRIs.
    """

    ENTITY_TYPE = "http://www.w3.org/1999/02/22-rdf-syntax-ns#type"


class EntityIRI(CaseInsensitiveEnum):
    """
    Enum for RDF/OWL ontology entity types

    """

    CLASS = "http://www.w3.org/2002/07/owl#Class"
    OBJECT_PROPERTY = "http://www.w3.org/2002/07/owl#ObjectProperty"
    NAMED_INDIVIDUAL = "http://www.w3.org/2002/07/owl#NamedIndividual"
    ANNOTATION_PROPERTY = "http://www.w3.org/2002/07/owl#AnnotationProperty"

    @classmethod
    def resolve_entity_type(cls, assigned_types: list[str]):
        """
        Resolves the entity type for a vertex.

        Args:
            assigned_types (list): list of assigned entity types for a vertex

        Returns:
            EntityIRI: The first matching EntityIRI for the assigned RDF type URIs.

        Raises:
            ValueError: If no RDF types are assigned to the entity, or if none match known entity types.
        """

        if not assigned_types:
            raise ValueError("No RDF type(s) assigned to entity.")
        for member in cls:
            if member.value in assigned_types:
                return member
        raise ValueError(f"Unrecognized ontology entity type(s): {assigned_types}")


class AnnotationPropertyIRI(CaseInsensitiveEnum):
    """
    Enum for annotation property IRIs used in ontology term metadata extraction.
    """

    EDITOR_PREFERRED_LABEL = "http://purl.obolibrary.org/obo/IAO_0000111"
    LABEL = "http://www.w3.org/2000/01/rdf-schema#label"
    DEFINITION = "http://purl.obolibrary.org/obo/IAO_0000115"
    ID = "http://www.geneontology.org/formats/oboInOwl#id"
    HAS_EXACT_SYNONYM = "http://www.geneontology.org/formats/oboInOwl#hasExactSynonym"
    DEPRECATED = "http://www.w3.org/2002/07/owl#deprecated"

    @classmethod
    def is_stored_property(cls, iri: str):
        """
        Checks if the given IRI is a valid member of the annotation property enum.

        Args:
            iri (str): The IRI to validate.

        Returns:
            bool: True if valid, False otherwise.
        """
        try:
            cls(iri)
            return True
        except ValueError:
            return False


class OntologyTerm(__OntologyTerm):
    """
    Extension to OntologyTerm providing async database operations
    """

    run_id: int  # the algorithm invocation (run) identifier

    async def exists(self, session) -> bool:
        """
        Check if this OntologyTerm exists in the Reference.Ontology.term table by term_id.

        Args:
            session: SQLAlchemy async session.

        Returns:
            bool: True if the term exists, False otherwise.
        """
        stmt = text("SELECT TRUE FROM Reference.Ontology.term WHERE term_id = :term_id")
        result = await session.execute(stmt, {"term_id": self.term_id})
        # Cast to bool to catch None (not found)
        return bool(await result.scalar())

    @classmethod
    def get_field_iri(cls, field: str, preferred=True) -> str:
        """
        Returns (list) of property IRIs used to retrieve values of an OntologyTerm object
        """

        if field not in cls.get_model_fields():
            raise ValueError(f"Invalid field '{field}' for OntologyTerm.")

        match field:
            case "term":
                if preferred:
                    return AnnotationPropertyIRI.EDITOR_PREFERRED_LABEL
                else:
                    AnnotationPropertyIRI.LABEL
            case "definition":
                return AnnotationPropertyIRI.DEFINITION
            case "term_id":
                return AnnotationPropertyIRI.ID
            case "synonym":
                return AnnotationPropertyIRI.HAS_EXACT_SYNONYM
            case "is_deprecated":
                return AnnotationPropertyIRI.DEPRECATED
            case _:
                raise ValueError(f"No property IRI mapping required for '{field}'.")

    async def fetch_term_id(self, session):
        """
        Return the term_id for this OntologyTerm from Reference.Ontology.term using
        the term field.

        Args:
            session: SQLAlchemy async session.

        Returns:
            str: The term_id if found.

        Raises:
            ValueError: If more than one term_id is found for the term.
            sqlalchemy.exc.NoResultFound: If no term_id is found for the term.
        """

        stmt = text("SELECT term_id FROM Reference.Ontology.term WHERE term = :term")
        result = await session.execute(stmt, {"term": self.term})
        term_ids = [row[0] for row in result.fetchall()]
        if len(term_ids) > 1:
            raise ValueError(
                f"Multiple term_ids found for term '{self.term}': {term_ids}"
            )
        if not term_ids:
            raise NoResultFound(f"No term_id found for term '{self.term}'")
        return term_ids[0]

    async def fetch_term_iri(self, session):
        """
        Return the term_iri for this OntologyTerm from Reference.Ontology.term using
        the term or term_id field.

        Args:
            session: SQLAlchemy async session.

        Returns:
            str: The term_iri if found.

        Raises:
            ValueError: If more than one term_iri is found for the term or term_id.
            sqlalchemy.exc.NoResultFound: If no term_iri is found for the term or term_id.
        """
        if self.term_id:
            stmt = text(
                "SELECT term_iri FROM Reference.Ontology.term WHERE term_id = :term_id"
            )
            result = await session.execute(stmt, {"term_id": self.term_id})
        else:
            stmt = text(
                "SELECT term_iri FROM Reference.Ontology.term WHERE term = :term"
            )
            result = await session.execute(stmt, {"term": self.term})

        term_IRIs = [row[0] for row in result.fetchall()]
        if len(term_IRIs) > 1:
            raise ValueError(
                f"Multiple IRIs found for term '{self.term or self.term_id}': {term_IRIs}"
            )
        if not term_IRIs:
            raise NoResultFound(f"No IRI found for term '{self.term or self.term_id}'")
        return term_IRIs[0]

    async def insert_placeholder(self, session):
        """
        Insert a placeholder ontology term vertex with only an IRI and category.

        Args:
            session: SQLAlchemy async session.

        Raises:
            IntegrityError: If the insert fails due to a duplicate or constraint.
        """

        stmt = text(
            """
            INSERT INTO Reference.Ontology.term (term_id, term_iri, run_id)
            VALUES (:term_id, :term_iri, :run_id)
            """
        )
        await session.execute(
            stmt,
            {
                "term_id": self.term_id,
                "term_iri": self.term_iri,
                "is_placeholder": True,
                "run_id": self.run_id,
            },
        )

    async def update_placeholder(self, session):
        """
        Update an existing placeholder ontology term with full details.
        Only updates if is_placeholder is True and term_id matches.

        Args:
            session: SQLAlchemy async session.
        """
        stmt = text(
            """
            UPDATE Reference.Ontology.term
            SET term_iri = :term_iri,
                term = :term,
                label = :label,
                definition = :definition,
                synonyms = :synonyms,
                is_deprecated = :is_deprecated,
                is_placeholder = FALSE,
                run_id = :run_id
            WHERE term_id = :term_id AND is_placeholder = TRUE
            """
        )
        await session.execute(
            stmt,
            {
                "term_id": self.term_id,
                "term_iri": self.term_iri,
                "term": self.term,
                "label": self.label,
                "definition": self.definition,
                "synonyms": self.synonyms,
                "is_deprecated": self.is_deprecated,
                "run_id": self.run_id,
            },
        )

    async def link_xdbref(self, xdbref_id: int, session):
        stmt = text(
            """
            INSERT INTO Reference.Ontology.defined_in (SOURCE, DESTINATION, run_id)
            """
        )

    async def insert(self, session):
        """
        Insert this OntologyTerm into the Reference.Ontology.term table.

        Args:
            session: SQLAlchemy async session.

        Returns:
            None

        Raises:
            IntegrityError: If the insert fails due to a duplicate or constraint.
        """
        stmt = text(
            """
            INSERT INTO Reference.Ontology.term (
                term_id, term_iri, term, label, definition, synonyms,
                is_deprecated, run_id
            ) VALUES (
                :term_id, :term_iri, :term, :label, :definition, :synonyms,
                :is_deprecated, :run_id
            )
            """
        )
        await session.execute(stmt, self.model_dump())

    # -------------------------
    # Duplicate Term Handlers
    # -------------------------

    def in_namespace(self, namespace) -> bool:
        """
        Check if this term's IRI starts with the given namespace.

        Args:
            namespace (str): The namespace URI to check.

        Returns:
            bool: True if term_iri starts with namespace, else False.
        """
        return self.term_iri.startswith(namespace)

    def _resolve_definition(self, stored_term_definition: str, namespace: str) -> str:
        """
        Select the preferred definition for a duplicate ontology term.

        Prefers the definition from the source ontology if available. Otherwise,
        selects the definition with lower Jaccard similarity and longer length.
        If only one definition is present, returns it.

        Args:
            stored_term_definition (str): Existing definition string.
            namespace (str): Source ontology namespace.

        Returns:
            str: Preferred definition string.
        """
        if not stored_term_definition:
            return self.definition
        if not self.definition:
            return stored_term_definition

        # Prefer new if it comes from the source ontology
        if self.in_namespace(namespace):
            return self.definition

        similarity = jaccard_word_similarity(stored_term_definition, self.definition)
        is_longer = len(self.definition) > len(stored_term_definition)
        if similarity < 0.5 and is_longer:
            return self.definition

        # Otherwise, keep existing
        return stored_term_definition


class OntologyTriple(__OntologyTriple):
    run_id: int  # the algorithm invocation (run) identifier


class OntologyRestriction(BaseModel):
    run_id: int  # the algorithm invocation (run) identifier
    triples: list[OntologyTriple]
