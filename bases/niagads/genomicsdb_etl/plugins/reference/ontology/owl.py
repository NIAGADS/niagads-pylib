"""
Ontology Loader Plugins
- Parse OWL files and load ontology terms into Reference.OntologyTerm or the (Public).OntologyGraph
Loads an ontology from an OWL file into the reference ontology graph schema.
"""

from datetime import datetime, timezone
from typing import Any, Dict, Iterator, List, Optional

from niagads.common.core import ComponentBaseMixin
from niagads.common.reference.ontologies.helpers import get_field_iri
from niagads.common.reference.ontologies.types import (
    AnnotationPropertyIRI,
    EntityTypeIRI,
    RDFPropertyIRI,
)
from niagads.common.types import ETLOperation
from niagads.database.genomicsdb.schema.admin.catalog import TableCatalog
from niagads.database.genomicsdb.schema.admin.types import TableRef
from niagads.database.genomicsdb.schema.ragdoc.chunks import (
    ChunkEmbedding,
    ChunkMetadata,
)
from niagads.database.genomicsdb.schema.ragdoc.types import RAGDocType
from niagads.database.genomicsdb.schema.reference.externaldb import ExternalDatabase
from niagads.database.genomicsdb.schema.reference.ontology import OntologyTerm
from niagads.etl.plugins.base import AbstractBasePlugin
from niagads.etl.plugins.metadata import PluginMetadata
from niagads.etl.plugins.parameters import BasePluginParams, PathValidatorMixin
from niagads.etl.plugins.registry import PluginRegistry
from niagads.etl.plugins.types import ETLLoadStrategy, ResumeCheckpoint
from niagads.genomicsdb_etl.plugins.common.mixins.parameters import (
    ExternalDatabaseRefMixin,
)
from niagads.nlp.embeddings import TextEmbeddingGenerator
from niagads.nlp.llm_types import LLM, NLPModelType
from pydantic import BaseModel, Field, field_validator
from rdflib import BNode, Graph, Literal, URIRef
from sqlalchemy.exc import NoResultFound  # TODO Wrap


class EmbeddedOntologyTerm(BaseModel, arbitrary_types_allowed=True):
    term: OntologyTerm
    chunk_text: str
    chunk_hash: bytes
    embedding: Optional[list] = None  # so it can be set in batch


# FIXME - just use ontologygraphtriple
class Triple(BaseModel):
    subject: str
    predicate: str
    object: str

    def __str__(self):
        return f"{str(self.subject)} -> {str(self.predicate)} -> {str(self.object)}"


class OWLLoaderParams(BasePluginParams, PathValidatorMixin, ExternalDatabaseRefMixin):
    file: str = Field(..., description="full path to OWL file")
    update_existing: Optional[bool] = Field(
        default=False,
        description="if term already exists in the table, attempts to update defintion and synonyms if necessary; if set to false, just skips existing terms",
    )
    validate_file_exists = PathValidatorMixin.validator("file", is_dir=False)


class OntologyTermReferenceLoaderParams(OWLLoaderParams):
    embedding_model: Optional[LLM] = Field(
        LLM.ALL_MINILM_L6_V2,
        description="LLM model for generating text embeddings",
    )
    embedding_batch_size: Optional[int] = Field(
        default=128, description="batch size for calculating embeddings"
    )

    @field_validator("embedding_model")
    @classmethod
    def validate_embedding_model(cls, v: LLM) -> LLM:
        """Validate that embedding_model is in allowed embedding models list."""
        LLM.validate(v, NLPModelType.EMBEDDING)
        return LLM(v)


class OWLParser(ComponentBaseMixin):
    def __init__(
        self, owl_file: str, logger=None, debug: bool = False, verbose: bool = False
    ):
        super().__init__(debug=debug, verbose=verbose)
        if logger is not None:
            self.logger = logger
        self._graph = Graph()
        self.logger.info("Initializing parser")
        self._graph.parse(owl_file, format="xml")

    def __resolve_entity_type(self, node) -> EntityTypeIRI:
        assigned_types = [
            str(obj)
            for obj in self._graph.objects(
                node, URIRef(str(RDFPropertyIRI.ENTITY_TYPE))
            )
        ]
        return EntityTypeIRI.resolve_entity_type(assigned_types)

    def __build_term(
        self, entity_iri, entity_type: EntityTypeIRI, entity_properties: dict
    ):
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
        affected_tables=[ChunkEmbedding, ChunkMetadata, OntologyTerm],
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

    def __init__(
        self,
        params: Dict[str, Any],
        name: Optional[str] = None,
        debug: bool = False,
        verbose: bool = False,
    ):
        super().__init__(params, name, debug, verbose)
        self.__embedding_generator = None
        self.__external_database = None
        self.__table_ref = None
        self.__processed_record_count = 0

    async def on_run_start(self, session):
        """on run start hook override"""

        self.__embedding_generator = TextEmbeddingGenerator(
            self._params.embedding_model
        )
        if self.__embedding_generator.is_cpu_limited:
            if self._params.embedding_batch_size > 128:
                self.logger.warning(
                    "CPU detected; batch sizes > 128 may cause slowdowns or high memory use when calculating embeddings."
                )
        elif self._params.embedding_batch_size > 512:
            self.logger.warning(
                "GPU detected; batch sizes > 512 may cause slowdowns or high memory use when calculating embeddings."
            )

        # one-off-lookups

        # validate the xdbref against the database
        self.__external_database: ExternalDatabase = (
            await self._params.fetch_xdbref(session) if self.is_etl_run else None
        )

        self.logger.debug(
            f"external_database_id = {self.__external_database.external_database_id}"
        )

        # for table_id in chunmk_metadata
        self.__table_ref: TableRef = await TableCatalog.get_table_ref(
            session, OntologyTerm
        )

    def get_record_id(self, record: OntologyTerm) -> str:
        """
        Returns a unique identifier for a record (subject URI).
        """
        return record.source_id

    def extract(self) -> Iterator[Any]:

        self.logger.debug("Entering Extract")
        parser = OWLParser(
            self._params.file,
            logger=self.logger,
            debug=self._debug,
            verbose=self._verbose,
        )

        # split into "embedding" batch-sized batches to pass to transform
        batch = []
        for term in parser.extract_terms():
            batch.append(term)
            if len(batch) >= self._params.embedding_batch_size:
                yield batch
                batch = []
        if len(batch) > 0:  # residuals
            yield batch

    def __generate_chunk_text(self, term: OntologyTerm) -> EmbeddedOntologyTerm:
        chunk_text: str = (
            f"Term: {term.term}\nLabel: {term.label}"
            f"\nCURIE: {term.source_id}\nDefinition: {term.definition}"
        )
        for s in term.synonyms:
            chunk_text += f"\nSynonym: {s}"

        if self._verbose:
            self.logger.debug(f"Chunk Text: {chunk_text}")

        return EmbeddedOntologyTerm(
            term=term,
            chunk_text=chunk_text,
            chunk_hash=self.__embedding_generator.hash_text(chunk_text),
        )

    def __generate_embedded_term(self, term: OntologyTerm) -> EmbeddedOntologyTerm:
        """generate embeddings for a single term"""
        embedded_term = self.__generate_chunk_text(term)
        embedded_term.embedding = self.__embedding_generator.generate(
            embedded_term.chunk_text, as_list=True
        )
        return embedded_term

    def transform(self, records: list[dict]) -> EmbeddedOntologyTerm:
        """
        Convert a list of record (OWL entity) dicts to an OntologyTerms and generate embeddings
        in batches
        """
        if records is None or (isinstance(records, list) and len(records) == 0):
            raise RuntimeError(
                "No records provided to transform(). At least one record is required."
            )

        embedded_ontology_terms = []
        text = []
        for record in records:
            record["source_id"] = record.pop("curie")
            term = OntologyTerm(**record)
            term.run_id = self.run_id
            term.external_database_id = self.__external_database.external_database_id

            if self._verbose:
                self.logger.debug(f"Term: {term.model_dump()}")

            embedded_term = self.__generate_chunk_text(term)
            embedded_ontology_terms.append(embedded_term)
            text.append(embedded_term.chunk_text)

        embeddings = self.__embedding_generator.generate(text, as_list=False)

        term: EmbeddedOntologyTerm
        for index, term in enumerate(embedded_ontology_terms):
            term.embedding = embeddings[index].tolist()

        self.__processed_record_count += self._params.embedding_batch_size
        self.logger.info(
            f"Calcualted embeddings for {self.__processed_record_count} ontology terms."
        )

        return embedded_ontology_terms

    async def __load_embedding(
        self,
        session,
        embedded_term: EmbeddedOntologyTerm,
        is_updated_record: bool = False,
    ):

        if is_updated_record:
            # pull records to update from the database
            chunk_metadata = ChunkMetadata.fetch_record(
                session,
                filters={
                    "table_id": self.__table_ref.table_id,
                    "row_id": embedded_term.term.ontology_term_id,
                },
            )

            chunk_embedding = ChunkEmbedding.fetch_record(
                session,
                filters={
                    "chunk_metadata_id": chunk_metadata.chunk_metadata_id,
                    "chunk_hash": chunk_metadata.chunk_hash,
                },
            )

            # update
            chunk_metadata.document_hash = embedded_term.chunk_hash
            chunk_metadata.chunk_hash = embedded_term.chunk_hash
            chunk_metadata.chunk_text = embedded_term.chunk_text
            chunk_metadata.update(session)

            chunk_embedding.chunk_hash = embedded_term.chunk_hash
            chunk_embedding.embedding = embedded_term.embedding
            chunk_embedding.embedding_model = str(self._params.embedding_model)
            chunk_embedding.embedding_date = datetime.now(tz=timezone.utc).isoformat()
            chunk_embedding.embedding_run_id = self.run_id
            chunk_embedding.update(session)

        else:  # build fresh and submit
            chunk_metadata: ChunkMetadata = ChunkMetadata(
                table_id=self.__table_ref.table_id,
                row_id=embedded_term.term.ontology_term_id,
                document_type=str(RAGDocType.ONTOLOGY),
                document_hash=embedded_term.chunk_hash,
                chunk_hash=embedded_term.chunk_hash,
                chunk_text=embedded_term.chunk_text,
                run_id=self.run_id,
            )

            await chunk_metadata.submit(session)

            chunk_embedding: ChunkEmbedding = ChunkEmbedding(
                chunk_metadata_id=chunk_metadata.chunk_metadata_id,
                chunk_hash=embedded_term.chunk_hash,
                embedding_model=str(self._params.embedding_model),
                embedding=embedded_term.embedding,
                embedding_date=datetime.now(tz=timezone.utc).isoformat(),
                embedding_run_id=self.run_id,
            )

            await chunk_embedding.submit(session)

    async def load(self, session, embedded_terms: List[EmbeddedOntologyTerm]):
        # Developers Note: ecords coming in are list b/c this is a chunked load -
        # the base buffers them until `batch_size`` is reached

        for e_term in embedded_terms:
            term = e_term.term

            try:
                existing_record: OntologyTerm = await OntologyTerm.fetch_record(
                    session, filters={"source_id": term.source_id}
                )

                if self._params.update_existing:
                    # if exists, update defintion, synonyms if need be
                    updated_definitions = await existing_record.resolve_definition(
                        session,
                        term.definition,
                        namespace=self.__external_database.database_key,
                    )

                    updated_synonyms = await existing_record.resolve_synonyms(
                        session, term.synonyms
                    )

                    if updated_definitions or updated_synonyms:
                        self.inc_tx_count(OntologyTerm, ETLOperation.UPDATE)

                        # if the term was defined in the current namespace, update
                        # the external db reference as well
                        if await existing_record.in_namespace(
                            session, self.__external_database.database_key
                        ):
                            existing_record.external_database_id = (
                                self.__external_database.external_database_id
                            )
                            await existing_record.update(session)

                        await self.__load_embedding(
                            session,
                            self.__generate_embedded_term(existing_record),
                            is_updated_record=True,
                        )
                    else:
                        self.inc_tx_count(OntologyTerm, ETLOperation.SKIP)
                else:
                    self.inc_tx_count(OntologyTerm, ETLOperation.SKIP)

            except NoResultFound:  # not found in DB, submit
                await term.submit(session)
                await self.__load_embedding(session, e_term)

        return ResumeCheckpoint(full_record=embedded_terms[-1].term)
