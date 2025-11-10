"""
OntologyOWLLoader Plugin

Loads an ontology from an OWL file into the reference ontology graph schema.

Follows niagads-pylib GenomicsDB ETL plugin conventions.
While it can be adapted for another application, it relies on the existence of a
`Reference.ExternalDatabse` table, creates virtual edges linking
each term to its source ontology, which is recorded as a row in the table.
"""

from typing import Any, Dict, Iterator, List, Optional, Type, Union

from niagads.common.models.ontology import RDFTermCategory
from niagads.etl.plugins.base import AbstractBasePlugin, LoadStrategy
from niagads.etl.plugins.logger import ETLOperation
from niagads.etl.plugins.parameters import (
    BasePluginParams,
    PathValidatorMixin,
    ResumeCheckpoint,
)
from niagads.etl.plugins.registry import PluginRegistry
from niagads.genomicsdb.models.admin.pipeline import ETLOperation
from niagads.genomicsdb_service.etl.plugins.db_helpers.ontologies import (
    OntologyPropertyIRI,
    OntologyRelationship,
    OntologyTerm,
)
from niagads.genomicsdb_service.etl.plugins.mixins.parameters import (
    ExternalDatabaseRefMixin,
)
from pydantic import Field
from rdflib import Graph
from rdflib.namespace import OWL
from sqlalchemy.exc import IntegrityError
from sqlalchemy.sql import text


class OntologyGraphLoaderParams(
    BasePluginParams, PathValidatorMixin, ExternalDatabaseRefMixin
):
    file: str

    # XXX: asking for this here b/c it seems too needlessly complex to pull
    # it out of the file
    namespace: str = Field(..., description="ontology base URI")

    validate_file_exists = PathValidatorMixin.validator("file", is_dir=False)


@PluginRegistry.register(metadata={"version": 1.0})
class OntologyGraphLoader(AbstractBasePlugin):
    """
    ETL plugin for loading an ontology from an OWL file into the reference ontology graph schema.
    """

    _params: OntologyGraphLoaderParams  # type annotation

    def __init__(self, params: Dict[str, Any], name: Optional[str] = None):
        super().__init__(params, name)
        self._xdbref_id = self._params.resolve_xdbref()
        self._graph = None

    @classmethod
    def description(cls) -> str:
        return (
            "Loads an ontology (terms and relationships) from an OWL file into the "
            "Reference.Ontology graph schema. By default, extracts relationships for "
            "the following predicates: subClassOf, is_a, derives_from, part_of, has_part, "
            "develops_from, located_in. Additional RO relationships can be extracted "
            "by specifying their URI using the `--relationships` parameter."
        )

    @classmethod
    def parameter_model(cls) -> Type[BasePluginParams]:
        return OntologyGraphLoaderParams

    @property
    def operation(self) -> ETLOperation:
        return ETLOperation.INSERT

    @property
    def affected_tables(self) -> List[str]:
        return [
            "Reference.Ontology",
        ]

    @property
    def load_strategy(self) -> LoadStrategy:
        return LoadStrategy.CHUNKED

    def extract(self) -> Iterator[Any]:
        """
        Parses the OWL file and yields ontology terms and triples.
        For each subject in the RDF graph, if it is a recognized ontology type
        (class, property, or individual), yield an OntologyTermModel instance.
        Then, yield all RDF triples as OntologyTripleModel instances.
        This supports downstream graph construction.
        """

        self._graph = Graph()
        self._graph.parse(self._params.file, format="xml")

        property_predicates = OntologyPropertyIRI.list()
        for subject in self._graph.subjects():
            props = {}
            for predicate, obj in self._graph.predicate_objects(subject):
                pred_str = str(predicate)
                if pred_str not in property_predicates:
                    yield OntologyRelationship(
                        subject=str(subject),
                        predicate=pred_str,
                        object=str(obj),
                    )
                else:
                    props.setdefault(pred_str, []).append(str(obj))
            yield {"subject": str(subject), "properties": props}

    @staticmethod
    def _resolve_term_category(term_types: list) -> RDFTermCategory:
        """
        Returns the RDFTermCategory for a set of RDF type URIs, or raises ValueError if not recognized.
        """

        if str(OWL.Class) in term_types:
            return RDFTermCategory.CLASS
        elif str(OWL.ObjectProperty) in term_types:
            return RDFTermCategory.PROPERTY
        elif str(OWL.NamedIndividual) in term_types:
            return RDFTermCategory.INDIVIDUAL
        raise ValueError(f"Unrecognized ontology term type(s): {term_types}")

    def transform(
        self, record: Union[OntologyTerm, OntologyRelationship]
    ) -> Union[OntologyTerm, OntologyRelationship]:

        if record is None:
            raise RuntimeError(
                "No records provided to transform(). At least one record is required."
            )
        if isinstance(record, OntologyRelationship):
            return record

        # otherwise assemble term
        props: dict = record["properties"]

        term_types = set(props.get(OntologyTerm.get_property_iri("term_category"), []))
        term_category = self._resolve_term_category(term_types)
        label = props.get(OntologyTerm.get_property_iri("label"), [None])[0]
        term_id = props.get(OntologyTerm.get_property_iri("term_id"), [None])[0]
        definition = props.get(OntologyTerm.get_property_iri("definition"), [None])[0]
        synonyms = props.get(OntologyTerm.get_property_iri("synonyms"), [])
        is_deprecated = bool(
            props.get(OntologyTerm.get_property_iri("is_deprecated"), [False])[0]
        )

        return OntologyTerm(
            term_iri=record["subject"],
            term_id=term_id,
            term_category=term_category,
            term=label,
            definition=definition,
            synonyms=synonyms,
            is_deprecated=is_deprecated,
        )

    def get_record_id(self, record: Union[OntologyTerm, OntologyRelationship]) -> str:
        """
        Returns a unique identifier for a record (subject URI).
        """
        if isinstance(record, OntologyRelationship):
            return None
        else:
            return record.term_id

    # TODO: with ontology terms sometimes you may see a term first in the non-source
    # ontology and may want to update the properties, when you load the source
    # need to create an update behavior to load better or missing property values
    # TODO: add xdbref vectors on duplicates (i.e., this term in multiple ontologies)
    async def _load_term(self, session, term: OntologyTerm) -> ResumeCheckpoint:
        try:
            await term.insert(session)
            self.update_transaction_count(
                ETLOperation.INSERT, "Reference.Ontology_term"
            )
            return ResumeCheckpoint(full_record=term)

        # TODO: update logic?
        except IntegrityError:
            self.logger.warning(f"Duplicate term_id '{term.term_id}' skipped.")
            self.update_transaction_count(ETLOperation.SKIP, "Reference.Ontology_term")
            return 0

    async def _triple_exists(self, session, triple: OntologyRelationship) -> bool:
        result = await session.execute(
            text(
                """
                SELECT 1 FROM Reference.Ontology.triple
                WHERE subject = :subject AND predicate = :predicate AND object = :object
                LIMIT 1
                """
            ),
            triple.model_dump(),
        )
        return bool(result.scalar())

    async def _insert_triple(
        self, session, triple: OntologyRelationship
    ) -> ResumeCheckpoint:
        await session.execute(
            text(
                """
                INSERT INTO Reference.Ontology.triple (
                    subject, predicate, object
                ) VALUES (
                    :subject, :predicate, :object
                )
                """
            ),
            triple.model_dump(),
        )

    async def _load_ontology_triple(self, session, triple: OntologyRelationship) -> int:
        if await self._triple_exists(session, triple):
            self.logger.warning(
                f"Duplicate triple ({triple.subject}, {triple.predicate}, {triple.object}) skipped."
            )
            self.update_transaction_count(
                ETLOperation.SKIP, "Reference.Ontology_triple"
            )

        await self._insert_triple(session, triple)
        self.update_transaction_count(ETLOperation.INSERT, "Reference.Ontology_triple")

        return ResumeCheckpoint(full_record=triple)

    async def load(self, transformed: Any) -> ResumeCheckpoint:
        """
        Insert a single ontology term or triple record into the database using SQLAlchemy text queries.
        Args:
            transformed: OntologyTerm or OntologyTriple record to insert.
        Returns:
            ResumeCheckpoint
        """

        async with self._session_manager() as session:
            if isinstance(transformed, OntologyTerm):
                return await self._load_term(session, transformed)
            elif isinstance(transformed, OntologyRelationship):
                return await self._load_ontology_triple(session, transformed)
            else:
                raise TypeError(f"Unknown record type: {type(transformed)}")
