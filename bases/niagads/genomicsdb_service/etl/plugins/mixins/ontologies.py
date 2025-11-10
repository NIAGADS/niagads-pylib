from niagads.common.models.ontology import OntologyTerm, RDFTermCategory
from niagads.utils.string import jaccard_word_similarity
from sqlalchemy import text
from sqlalchemy.exc import NoResultFound


class OntologyTermDatabaseMixin(OntologyTerm):
    """
    Mixin for OntologyTerm providing async database operations
    """

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
            INSERT INTO Reference.Ontology.term (term_id, term_iri, term_category)
            VALUES (:term_id, :term_iri, :term_category)
            """
        )
        await session.execute(
            stmt,
            {
                "term_id": self.term_id,
                "term_iri": self.term_iri,
                "term_category": str(self.term_category),
            },
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
                is_obsolete, term_category
            ) VALUES (
                :term_id, :term_iri, :term, :label, :definition, :synonyms,
                :is_obsolete, :term_category
            )
            """
        )
        await session.execute(stmt, self.model_dump())

    # -------------------------
    # Duplicate Term Handlers
    # -------------------------

    def in_namespace(self, namespace) -> bool:
        """
        Returns True if the current ontology is the source of the
        the term.  Used to assess whether a duplicate term
        might need to be updated in the database.
        """
        return self.term_iri.startswith(namespace)

    def _resolve_definition(self, stored_term_definition: str, namespace: str) -> str:
        """
        Returns the preferred definition for a duplicated ontology term.

        Prefers the definition from the source ontology if available.
        Otherwise, selects the definition with lower Jaccard similarity
        and longer character length. If neither definition is present,
        returns the available one.

        Args:
            term: OntologyTerm.
            stored_term_definition: Existing definition string.

        Returns:
            str: The chosen definition string.
        """
        if not stored_term_definition:
            return self.definition
        if not self.definition:
            return stored_term_definition

        # Prefer new if it comes from the source ontology
        if self.in_namespace(self, namespace):
            return self.definition

        similarity = jaccard_word_similarity(stored_term_definition, self.definition)
        is_longer = len(self.definition) > len(stored_term_definition)
        if similarity < 0.5 and is_longer:
            return self.definition

        # Otherwise, keep existing
        return stored_term_definition
