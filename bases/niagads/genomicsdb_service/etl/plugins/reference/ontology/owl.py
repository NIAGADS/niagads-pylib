"""
Ontology Loader Plugins
- Parse OWL files and load ontology terms into Reference.OntologyTerm or the (Public).OntologyGraph
Loads an ontology from an OWL file into the reference ontology graph schema.
"""

from datetime import datetime, timezone
from typing import Any, Dict, Iterator, Optional, Union

from niagads.common.reference.ontologies.types import (
    AnnotationPropertyIRI,
    EntityTypeIRI,
    RDFPropertyIRI,
)
from niagads.common.reference.ontologies.helpers import get_field_iri
from niagads.etl.plugins.base import AbstractBasePlugin
from niagads.etl.plugins.metadata import PluginMetadata
from niagads.etl.plugins.parameters import BasePluginParams, PathValidatorMixin
from niagads.etl.plugins.registry import PluginRegistry
from niagads.etl.plugins.types import ETLLoadStrategy, ResumeCheckpoint
from niagads.etl.plugins.types import ETLOperation
from niagads.genomicsdb.schema.reference.externaldb import ExternalDatabase
from niagads.genomicsdb.schema.reference.ontology import (
    OntologyGraphTermVertex,
    OntologyTerm,
)
from niagads.genomicsdb_service.etl.plugins.common.mixins.parameters import (
    ExternalDatabaseRefMixin,
)
from niagads.nlp.embeddings import TextEmbeddingGenerator
from niagads.nlp.llm_types import LLM, NLPModelType
from pydantic import BaseModel, Field, field_validator
from rdflib import BNode, Graph, Literal, URIRef
from sqlalchemy.exc import NoResultFound  # TODO Wrap


# FIXME - just use ontologygraphtriple
class Triple(BaseModel):
    subject: str
    predicate: str
    object: str

    def __str__(self):
        return f"{str(self.subject)} -> {str(self.predicate)} -> {str(self.object)}"


class OWLLoaderParams(BasePluginParams, PathValidatorMixin, ExternalDatabaseRefMixin):
    file: str = Field(..., description="full path to OWL file")

    validate_file_exists = PathValidatorMixin.validator("file", is_dir=False)


class OntologyTermReferenceLoaderParams(OWLLoaderParams):
    embedding_model: LLM = Field(
        LLM.ALL_MINILM_L6_V2,
        description="LLM model for generating text embeddings",
    )

    @field_validator("embedding_model")
    @classmethod
    def validate_embedding_model(cls, v: LLM) -> LLM:
        """Validate that embedding_model is in allowed embedding models list."""
        LLM(v).validate(NLPModelType.EMBEDDING)
        return v


class OWLParser:
    def __init__(self, owl_file: str):
        self._graph = Graph()
        self._graph.parse(owl_file, format="xml")

    def __resolve_entity_type(self, node) -> EntityTypeIRI:
        assigned_types = [
            str(obj) for obj in self._graph.objects(node, RDFPropertyIRI.ENTITY_TYPE)
        ]
        return EntityTypeIRI.resolve_entity_type(assigned_types)

    @staticmethod
    def __build_term(entity_iri, entity_type: EntityTypeIRI, entity_properties: dict):
        label = entity_properties.get(get_field_iri("term", preferred=True), [None])[0]
        if label is None:  # no editor preffered label
            label = entity_properties.get(
                get_field_iri("term", preferred=False), [None]
            )[0]

        term_id = entity_properties.get(get_field_iri("term_id"), [None])[0]
        definition = entity_properties.get(get_field_iri("definition"), [None])[0]
        synonyms = entity_properties.get(get_field_iri("synonym"), [])
        is_deprecated = bool(
            entity_properties.get(get_field_iri("is_deprecated"), [False])[0]
        )

        return {
            "term_iri": entity_iri,
            "entity_type": str(entity_type),
            "curie": term_id,
            "term": label,
            "definition": definition,
            "synonyms": synonyms,
            "is_deprecated": is_deprecated,
        }

    def extract_terms(self) -> Iterator[dict]:
        """
        Extracts ontology term entities from the RDF graph.

        Iterates over all subjects in the RDF graph, resolves their entity type,
        and collects annotation properties. Yields a dictionary for each term
        with its IRI, type, and properties (label, definition, synonyms, etc.).

        Returns:
            Iterator[dict]: dict with fields that can be used to build OntologyTerm
                or OntologyTermVertex object as required by Plugin
        """
        for subject in self._graph.subjects():
            subject_iri = str(subject)

            try:
                subject_type: EntityTypeIRI = self.__resolve_entity_type(subject)
            except ValueError:
                continue  # skip the node

            subject_properties = {}
            for predicate, obj in self._graph.predicate_objects(subject):
                predicate_iri = str(predicate)
                object_iri = str(obj)

                if isinstance(obj, Literal):
                    if AnnotationPropertyIRI.is_stored_property(predicate_iri):
                        subject_properties.setdefault(predicate_iri, []).append(
                            object_iri
                        )

            yield self.__build_term(subject_iri, subject_type, subject_properties)

    def extract_triples(self) -> Iterator[Triple]:
        """
        Extracts ontology relationship triples from the RDF graph.

        Iterates over all subjects and their predicate-object pairs in the RDF graph.
        For each predicate that is an object property or entity type, yields a Triple
        object with subject, predicate, and object IRIs. Skips annotation properties
        and unsupported predicate types.

        Returns:
            Iterator[Triple]: Each Triple contains subject, predicate, and object IRIs.
        """
        for subject in self._graph.subjects():
            subject_iri = str(subject)

            try:
                self.__resolve_entity_type(subject)
            except ValueError:
                continue  # skip the node

            for predicate, obj in self._graph.predicate_objects(subject):
                predicate_iri = str(predicate)
                object_iri = str(obj)

                if isinstance(obj, URIRef):  # relation prop
                    # get the type of the predicate
                    try:
                        predicate_type = self.__resolve_entity_type(predicate)
                    except ValueError:
                        continue  # not a supported predicate type

                    # only keep triples that are not annotations
                    if (
                        predicate_type == EntityTypeIRI.OBJECT_PROPERTY
                        or predicate_iri == RDFPropertyIRI.ENTITY_TYPE
                    ):
                        yield Triple(
                            subject=subject_iri,
                            predicate=predicate_iri,
                            object=object_iri,
                        )

    def extract_restrictions(self):
        raise NotImplementedError()
        for subject in self._graph.subjects():
            subject_iri = str(subject)

            try:
                self.__resolve_entity_type(subject)
            except ValueError:
                continue  # skip the node

            subject_properties = {}
            for predicate, obj in self._graph.predicate_objects(subject):
                predicate_iri = str(predicate)
                object_iri = str(obj)

                if isinstance(obj, BNode):
                    continue
                    # Check if this BNode is an OWL restriction
                    # if (obj, RDF.type, OWL.Restriction) in self._graph:
                    #   ..


@PluginRegistry.register(
    PluginMetadata(
        version="1.0",
        description=(
            f"ETL Plugin to load ontology terms from an OWL file into {OntologyTerm.table_name()}."
            f"Loads terms, properties, and embeddings."
        ),
        affected_tables=[OntologyTerm],
        load_strategy=ETLLoadStrategy.CHUNKED,
        operation=ETLOperation.LOAD,
        is_large_dataset=False,
        parameter_model=OntologyTermReferenceLoaderParams,
    )
)
class OntologyTermLoader(AbstractBasePlugin):
    """
    ETL plugin for loading ontology terms from an OWL file into the reference ontologyterm table
    """

    _params: OntologyTermReferenceLoaderParams  # type annotation

    def __init__(self, params: Dict[str, Any], name: Optional[str] = None):
        super().__init__(params, name)
        self.__skips = 0
        self.__updates = 0

    async def on_run_start(self, session):
        """on run start hook override"""
        # validate the xdbref against the database
        self.__external_database: ExternalDatabase = (
            None if self.is_dry_run else await self._params.fetch_xdbref(session)
        )

        self.__embedding_generator = TextEmbeddingGenerator(
            self._params.embedding_model
        )

    def get_record_id(self, record: OntologyTerm) -> str:
        """
        Returns a unique identifier for a record (subject URI).
        """
        return record.source_id

    def extract(self) -> Iterator[Any]:
        parser = OWLParser(self._params.file)
        yield from parser.extract_terms()

    def __generate_term_embedding(self, term: OntologyTerm):
        term.embedding_date = datetime.now(tz=timezone.utc)
        term.embedding_model = str(self._params.embedding_model)
        term.embedding_run_id = self._run_id

        values = [term.term, term.label, term.definition, term.curie] + (
            term.synonyms or []
        )
        embedding_text = "|".join([v for v in values if v])
        term.embedding_hash = self.__embedding_generator.hash_text(embedding_text)
        term.embedding = self.__embedding_generator.generate(embedding_text)

    def transform(self, record: dict) -> OntologyTerm:
        """
        Convert a record (OWL entity) dict to an OntologyTerm and generate embedding.
        """
        if record is None:
            raise RuntimeError(
                "No records provided to transform(). At least one record is required."
            )

        record["source_id"] = record.pop("curie")
        term = OntologyTerm(**record)
        term.run_id = self._run_id
        term.external_database_id = self.__external_database.external_database_id

        try:
            self.__generate_term_embedding(term)
        except Exception as err:
            raise RuntimeError(
                f"Error generating embeddings for OntologyTerm: {term.source_id}"
            ) from err

        return term

    async def load(self, session, transformed: OntologyTerm):
        # try to retrieve from database
        transaction_count = 0
        try:
            existing_record: OntologyTerm = await OntologyTerm.fetch_record(
                session, filters={"curie": transformed.curie}
            )

            # if exists, update defintion, synonyms if need be
            updated_definitions = await existing_record.resolve_definition(
                session,
                transformed.definition,
                namespace=self.__external_database.database_key,
            )
            updated_synonyms = await existing_record.resolve_synonyms(
                session, transformed.synonyms
            )
            if updated_definitions or updated_synonyms:
                self.__updates += (
                    1  # todo handle logging of updates/skips in after_run_complete?
                )
            else:
                self.__skips += 1
                # TODO - verbose/debug log skip?

        except NoResultFound:  # not found in DB, submit
            await transformed.submit(session)
            self.update_transaction_count(
                ETLOperation.INSERT, OntologyTerm.table_name()
            )
        finally:
            return (ResumeCheckpoint(full_record=transformed),)


@PluginRegistry.register(
    PluginMetadata(
        version="1.0",
        description=(
            f"ETL Plugin to load ontology terms from an OWL file into {OntologyTerm.table_name()}."
            f"the knowledge graph"
        ),
        affected_tables=[OntologyTerm],  # FIXME - this is not the graph model
        load_strategy=ETLLoadStrategy.CHUNKED,
        operation=ETLOperation.INSERT,
        is_large_dataset=False,
        parameter_model=OWLLoaderParams,
    )
)
class OntologyGraphLoader(AbstractBasePlugin):
    """
    ETL plugin for loading an ontology from an OWL file into the reference ontology graph schema.
    """

    _params: OWLLoaderParams  # type annotation

    def __init__(self, params: Dict[str, Any], name: Optional[str] = None):
        super().__init__(params, name)

    async def on_run_start(self, session):
        """on run start hook override"""
        # validate the xdbref against the database
        self._xdbref_id = (
            None if self.is_dry_run else await self._params.resolve_xdbref(session)
        )

    def extract(self) -> Iterator[Any]:
        parser = OWLParser(self._params.file)
        yield from parser.extract_terms()
        yield from parser.extract_triples()
        # yield from parser.extract_restrictions()

    def transform(
        self, record: Union[dict, Triple]
    ) -> Union[OntologyGraphTermVertex, Triple]:

        if record is None:
            raise RuntimeError(
                "No records provided to transform(). At least one record is required."
            )
        if isinstance(record, Triple):
            return record

        return OntologyGraphTermVertex(**record)

    def get_record_id(self, record) -> str:
        """
        Returns a unique identifier for a record (subject URI).
        """
        if isinstance(record, Triple):
            return str(Triple)
        else:
            return record.term_id

    # FIXME: these are all wrong now
    # NOTE: insert term needs to check against OntologyTerm relational table for ontology_term_id and definition
    async def load(self, transformed: Any, session) -> ResumeCheckpoint:
        """
        Insert a single ontology term or triple record into the database using SQLAlchemy text queries.
        Args:
            transformed: OntologyTerm or OntologyTriple record to insert.
        Returns:
            ETLLoadResult
        """
        ontology_id = self._params.resolve_xdbref()
        raise NotImplementedError()

    def on_run_complete(self) -> None:
        return None
