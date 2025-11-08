"""
OntologyOWLLoader Plugin

Loads an ontology from an OWL file into the reference ontology graph schema.

Follows niagads-pylib ETL plugin conventions and Polylith architecture.
"""

from enum import auto
from typing import Any, Dict, Iterator, List, Optional, Type, Union

from niagads.enums.core import CaseInsensitiveEnum
from niagads.etl.plugins.base import AbstractBasePlugin, LoadStrategy
from niagads.etl.plugins.logger import ETLOperation
from niagads.etl.plugins.parameters import (
    BasePluginParams,
    ExternalDatabaseMixin,
    PathValidatorMixin,
)
from niagads.genomicsdb.models.admin.pipeline import ETLOperation
from niagads.etl.plugins.registry import PluginRegistry
from pydantic import BaseModel, Field, model_validator
from rdflib import Graph, URIRef
from rdflib.namespace import OWL, RDF, RDFS
from sqlalchemy.sql import text
from sqlalchemy.exc import IntegrityError

OBOINOWL = URIRef("http://www.geneontology.org/formats/oboInOwl#hasExactSynonym")
IAO = URIRef("http://purl.obolibrary.org/obo/IAO_0100001")


class RDFTermCategory(CaseInsensitiveEnum):
    CLASS = auto()
    PROPERTY = auto()
    INDIVIDUAL = auto()

    def __str__(self):
        return self.value.lower()

    @classmethod
    def from_term(cls, term_types):
        """
        Returns the RDFTermCategory for a set of RDF type URIs, or raises ValueError if not recognized.
        """

        if str(OWL.Class) in term_types:
            return cls.CLASS
        elif str(OWL.ObjectProperty) in term_types:
            return cls.PROPERTY
        elif str(OWL.NamedIndividual) in term_types:
            return cls.INDIVIDUAL
        raise ValueError(f"Unrecognized ontology term type(s): {term_types}")


class OntologyTerm(BaseModel):
    term_id: str
    term_category: str
    label: str | None = None
    definition: str | None = None
    synonyms: list[str] = Field(default_factory=list)
    is_obsolete: bool = False
    replaced_by: str | None = None

    @model_validator(mode="before")
    def convert_fields(cls, values):
        for field, v in values.items():
            if v is not None and not isinstance(v, bool):
                values[field] = str(v)
        return values


class OntologyTriple(BaseModel):
    subject: str
    predicate: str
    object: str


class OntologyGraphLoaderParams(
    BasePluginParams, PathValidatorMixin, ExternalDatabaseMixin
):
    file: str
    validate_file_exists = PathValidatorMixin.validator("file", is_dir=False)


@PluginRegistry.register(metadata={"version": 1.0})
class OntologyGraphLoader(AbstractBasePlugin):
    """
    ETL plugin for loading an ontology from an OWL file into the reference ontology graph schema.

    Args:
        params (OntologyOWLLoaderParams): Plugin parameters.
        name (Optional[str]): Plugin name.
    """

    def __init__(self, params: Dict[str, Any], name: Optional[str] = None):
        super().__init__(params, name)
        self._owl_path = self._params.owl_path
        self._graph = None

    @classmethod
    def description(cls) -> str:
        return "Loads an ontology (terms and relationships) from an OWL file into the Reference.Ontology graph schema. "

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
        return LoadStrategy.STREAMING

    def extract(self) -> Iterator[Any]:
        """
        Parses the OWL file and yields ontology terms and triples.
        For each subject in the RDF graph, if it is a recognized ontology type
        (class, property, or individual), yield an OntologyTermModel instance.
        Then, yield all RDF triples as OntologyTripleModel instances.
        This supports downstream graph construction.
        """

        self._graph = Graph()
        self._graph.parse(self._owl_path, format="xml")

        # Extract ontology terms
        for term in self._graph.subjects():

            term_types = set(str(o) for o in self._graph.objects(term, RDF.type))
            term_category = RDFTermCategory.from_term(term_types)

            label = self._graph.value(term, RDFS.label)
            definition = self._graph.value(term, RDFS.comment)
            synonyms = [str(s) for s in self._graph.objects(term, OBOINOWL)]
            is_obsolete = bool(self._graph.value(term, OWL.deprecated))
            replaced_by = self._graph.value(term, IAO)

            yield OntologyTerm(
                term_id=str(term),
                term_category=term_category,
                label=label,
                definition=definition,
                synonyms=synonyms,
                is_obsolete=is_obsolete,
                replaced_by=replaced_by,
            )

        # Extract ontology triples
        for s, p, o in self._graph:
            yield OntologyTriple(
                subject=str(s),
                predicate=str(p),
                object=str(o),
            )

    def transform(
        self, data: Union[OntologyTerm, OntologyTriple]
    ) -> Union[OntologyTerm, OntologyTriple]:
        if self._debug:
            self.logger.debug("Transforming data", data)
        if data is None:
            raise RuntimeError(
                "No records provided to transform(). At least one record is required."
            )
        return data

    def get_record_id(self, record: Any) -> str:
        """
        Returns a unique identifier for a record (subject URI).
        """
        return record.get("subject", "")

    async def _load_term(self, session, term: OntologyTerm) -> int:
        try:
            await session.execute(
                text(
                    """
                    INSERT INTO Reference.Ontology.term (
                        term_id, term, label, definition, synonyms, is_obsolete, replaced_by, term_category
                    ) VALUES (
                        :term_id, :term, :label, :definition, :synonyms, :is_obsolete, :replaced_by, :term_category
                    )
                    """
                ),
                term.model_dump(),
            )
            self.update_transaction_count(
                ETLOperation.INSERT, "Reference.Ontology.term"
            )
            return 1

        except IntegrityError:
            self.logger.warning(f"Duplicate term_id '{term.term_id}' skipped.")
            self.update_transaction_count(ETLOperation.SKIP, "Reference.Ontology.term")
            return 0

    async def _triple_exists(self, session, triple: OntologyTriple) -> bool:
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

    async def _insert_triple(self, session, triple: OntologyTriple) -> None:
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

    async def _load_ontology_triple(self, session, triple: OntologyTriple) -> int:
        if await self._triple_exists(session, triple):
            self.logger.warning(
                f"Duplicate triple ({triple.subject}, {triple.predicate}, {triple.object}) skipped."
            )
            self.update_transaction_count(
                ETLOperation.SKIP, "Reference.Ontology.triple"
            )
            return 0
        await self._insert_triple(session, triple)
        self.update_transaction_count(ETLOperation.INSERT, "Reference.Ontology.triple")
        return 1

    async def load(self, transformed: Any) -> int:
        """
        Insert a single ontology term or triple record into the database using SQLAlchemy text queries.
        Args:
            transformed: OntologyTerm or OntologyTriple record to insert.
        Returns:
            int: Number of records inserted (always 1 if successful).
        """
        if transformed is None:
            raise RuntimeError("No record provided to load(). A record is required.")

        async with self._session_manager() as session:
            if isinstance(transformed, OntologyTerm):
                return await self._insert_ontology_term(session, transformed)
            elif isinstance(transformed, OntologyTriple):
                return await self._load_ontology_triple(session, transformed)
            else:
                raise TypeError(f"Unknown record type: {type(transformed)}")
