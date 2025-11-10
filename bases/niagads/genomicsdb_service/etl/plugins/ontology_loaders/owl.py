"""
OntologyOWLLoader Plugin

Loads an ontology from an OWL file into the reference ontology graph schema.

Follows niagads-pylib GenomicsDB ETL plugin conventions.
While it can be adapted for another application, it relies on the existence of a
`Reference.ExternalDatabse` table, creates virtual edges linking
each term to its source ontology, which is recorded as a row in the table.
"""

from enum import auto
from typing import Any, Dict, Iterator, List, Optional, Type, Union

from niagads.enums.core import CaseInsensitiveEnum
from niagads.etl.plugins.base import AbstractBasePlugin, LoadStrategy
from niagads.etl.plugins.logger import ETLOperation
from niagads.etl.plugins.parameters import (
    BasePluginParams,
    PathValidatorMixin,
    ResumeCheckpoint,
)
from niagads.genomicsdb.models.admin.pipeline import ETLOperation
from niagads.etl.plugins.registry import PluginRegistry
from niagads.genomicsdb_service.etl.plugins.mixins.parameters import (
    ExternalDatabaseRefMixin,
)
from pydantic import BaseModel, Field, computed_field, model_validator
from rdflib import Graph, URIRef
from rdflib.namespace import OWL, RDF, RDFS
from sqlalchemy.sql import text
from sqlalchemy.exc import IntegrityError

OBOINOWL = URIRef("http://www.geneontology.org/formats/oboInOwl#hasExactSynonym")
IAO = URIRef("http://purl.obolibrary.org/obo/IAO_0100001")

OBO_IS_A = "http://www.geneontology.org/formats/oboInOwl#is_a"
RO_DERVICES_FROM = "http://purl.obolibrary.org/obo/RO_0001000"
RO_PART_OF = "http://purl.obolibrary.org/obo/BFO_0000050"
RO_HAS_PART = "http://purl.obolibrary.org/obo/BFO_0000051"
RO_DEVELOPS_FROM = "http://purl.obolibrary.org/obo/RO_0002202"
RO_LOCATED_IN = "http://purl.obolibrary.org/obo/RO_0001025"

RELATIONSHIP_PREDICATES = [
    str(RDFS.subClassOf),
    OBO_IS_A,
    RO_DERVICES_FROM,
    RO_PART_OF,
    RO_HAS_PART,
    RO_DEVELOPS_FROM,
    RO_LOCATED_IN,
]


class RDFTermCategory(CaseInsensitiveEnum):
    """
    Enum for RDF/OWL ontology term categories.

    Values:
        CLASS: OWL class
        PROPERTY: OWL property
        INDIVIDUAL: OWL named individual
    """

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
    """
    Pydantic model representing a term in an ontology graph.

    Used for storing ontology term metadata, including category, label,
    definition, synonyms, and obsolescence information.
    """

    uri: str = Field(..., description="Unique identifier for the ontology term (URI)")
    term_category: str = Field(
        ..., description="Term category: class, property, or individual"
    )
    label: str | None = Field(
        default=None, description="Human-readable label for the term"
    )
    definition: str | None = Field(
        default=None, description="Textual definition of the term"
    )
    synonyms: list[str] = Field(
        default_factory=list, description="List of synonyms for the term"
    )
    is_obsolete: bool = Field(default=False, description="True if the term is obsolete")
    replaced_by: str | None = Field(
        default=None, description="URI of the term that replaces this one, if obsolete"
    )

    @computed_field
    @property
    def term_id(self) -> str:
        """
        Returns the short ID for the ontology term, computed from the URI.
        """
        base = self.uri.rsplit("/", 1)[-1]
        return base.replace("_", ":") if "_" in base and base.count("_") == 1 else base

    @model_validator(mode="before")
    def convert_fields(cls, values):
        """
        Converts all non-boolean field values to strings before model validation.

        Args:
            values (dict): Dictionary of field values.

        Returns:
            dict: Updated field values with non-boolean values converted to strings.
        """
        for field, v in values.items():
            if v is not None and not isinstance(v, bool):
                values[field] = str(v)
        return values


class OntologyTriple(BaseModel):
    """
    Pydantic model representing an RDF triple in the ontology graph.

    Each triple consists of a subject, predicate, and object URI or value.
    """

    subject: str
    predicate: str
    object: str


class OntologyGraphLoaderParams(
    BasePluginParams, PathValidatorMixin, ExternalDatabaseRefMixin
):
    file: str
    relationships: list = Field(
        default_factory=list,
        description=(
            "List of RO relationship terms to extract. Example terms: has_target (RO_0002434), has_input "
            "(RO_0002233), has_output (RO_0002234), preceded_by (RO_0002001)."
        ),
    )

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
        self._relationship_predicates = (
            RELATIONSHIP_PREDICATES + self._params.relationships
        )
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

        for subject in self._graph.subjects():
            props = {}
            for predicate, obj in self._graph.predicate_objects(subject):
                pred_str = str(predicate)
                if pred_str in self._relationship_predicates:
                    yield OntologyTriple(
                        subject=str(subject),
                        predicate=pred_str,
                        object=str(obj),
                    )
                else:
                    props.setdefault(pred_str, []).append(str(obj))
            yield {"subject": str(subject), "properties": props}

    def transform(
        self, record: Union[OntologyTerm, OntologyTriple]
    ) -> Union[OntologyTerm, OntologyTriple]:

        if record is None:
            raise RuntimeError(
                "No records provided to transform(). At least one record is required."
            )
        if isinstance(record, OntologyTriple):
            return record

        # otherwise assemble term
        props: dict = record["properties"]

        term_types = set(props.get(str(RDF.type), []))
        term_category = RDFTermCategory.from_term(term_types)
        label = props.get(str(RDFS.label), [None])[0]
        definition = props.get(str(RDFS.comment), [None])[0]
        synonyms = props.get(str(OBOINOWL), [])
        is_obsolete = bool(props.get(str(OWL.deprecated), [False])[0])
        replaced_by = props.get(str(IAO), [None])[0]

        return OntologyTerm(
            uri=record["subject"],
            term_category=term_category,
            label=label,
            definition=definition,
            synonyms=synonyms,
            is_obsolete=is_obsolete,
            replaced_by=replaced_by,
        )

    def get_record_id(self, record: Union[OntologyTerm, OntologyTriple]) -> str:
        """
        Returns a unique identifier for a record (subject URI).
        """
        if isinstance(record, OntologyTriple):
            return None
        else:
            return record.term_id

    async def _load_term(self, session, term: OntologyTerm) -> ResumeCheckpoint:
        try:
            await session.execute(
                text(
                    """
                    INSERT INTO Reference.Ontology.term (
                        term_id, uri, term, label, definition, synonyms, is_obsolete, replaced_by, term_category
                    ) VALUES (
                        :term_id, :uri, :term, :label, :definition, :synonyms, :is_obsolete, :replaced_by, :term_category
                    )
                    """
                ),
                term.model_dump(),
            )
            self.update_transaction_count(
                ETLOperation.INSERT, "Reference.Ontology.term"
            )
            return ResumeCheckpoint(full_record=term)

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

    async def _insert_triple(self, session, triple: OntologyTriple) -> ResumeCheckpoint:
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
        return ResumeCheckpoint(full_record=triple)

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
