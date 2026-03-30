"""
Ontology Loader Plugins
- Parse OWL files and load ontology terms into Reference.OntologyTerm or the (Public).OntologyGraph
Loads an ontology from an OWL file into the reference ontology graph schema.
"""

from datetime import datetime, timezone
from typing import Any, Dict, Iterator, List, Optional

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
from niagads.etl.plugins.types import ETLLoadStrategy
from niagads.genomicsdb_etl.plugins.common.mixins.parameters import (
    ExternalDatabaseRefMixin,
)
from niagads.nlp.embeddings import TextEmbeddingGenerator
from niagads.nlp.llm_types import LLM, NLPModelType
from niagads.ontology_parsers import OWLParser
from pydantic import BaseModel, Field, field_validator
from sqlalchemy.exc import NoResultFound


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
    validate_file_exists = PathValidatorMixin.validator("file")


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
        log_path: str = None,
        debug: bool = False,
        verbose: bool = False,
    ):
        super().__init__(params, name, log_path, debug, verbose)
        self.__embedding_generator = None
        self.__external_database = None
        self.__table_ref = None
        self.__processed_record_count = 0

    async def __fetch_existing_term(
        self, session, source_id: str
    ) -> Optional[OntologyTerm]:
        try:
            return await OntologyTerm.fetch_record(
                session, filters={"source_id": source_id}
            )
        except NoResultFound:
            return None

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
        if term.synonyms:
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
            term: OntologyTerm = OntologyTerm(**record)
            if term.label is None:
                term.label = term.term.replace("_", " ")

            term.run_id = self.run_id
            term.external_database_id = self.__external_database.external_database_id

            if self._verbose:
                self.logger.debug(f"Term: {term.model_dump()}")

            embedded_term = self.__generate_chunk_text(term)
            embedded_ontology_terms.append(embedded_term)
            text.append(embedded_term.chunk_text)

        embeddings = self.__embedding_generator.generate(text, as_list=False)

        eterm: EmbeddedOntologyTerm
        for index, eterm in enumerate(embedded_ontology_terms):
            eterm.embedding = embeddings[index].tolist()

        self.__processed_record_count += self._params.embedding_batch_size
        self.logger.info(
            f"Calcualted embeddings for {self.__processed_record_count} ontology terms."
        )

        return embedded_ontology_terms

    def __generate_chunk_metadata(self, term_records: list[EmbeddedOntologyTerm]):
        return [
            ChunkMetadata(
                table_id=self.__table_ref.table_id,
                row_id=embedded_term.term.ontology_term_id,
                document_type=str(RAGDocType.ONTOLOGY),
                document_hash=embedded_term.chunk_hash,
                chunk_hash=embedded_term.chunk_hash,
                chunk_text=embedded_term.chunk_text,
                run_id=self.run_id,
            )
            for embedded_term in term_records
        ]

    def __generate_chunk_embeddings(
        self, metadata: list[ChunkMetadata], term_records: list[EmbeddedOntologyTerm]
    ):
        return [
            ChunkEmbedding(
                chunk_metadata_id=chunk_metadata.chunk_metadata_id,
                chunk_hash=chunk_metadata.chunk_hash,
                embedding_model=str(self._params.embedding_model),
                embedding=term_records[index].embedding,
                embedding_date=datetime.now().isoformat(),
                embedding_run_id=self.run_id,
                run_id=self.run_id,
            )
            for index, chunk_metadata in enumerate(metadata)
        ]

    async def __update_embedding(self, session, embedded_term: EmbeddedOntologyTerm):

        # pull records to update from the database
        chunk_metadata: ChunkMetadata = await ChunkMetadata.fetch_record(
            session,
            filters={
                "table_id": self.__table_ref.table_id,
                "row_id": embedded_term.term.ontology_term_id,
            },
        )

        chunk_embedding: ChunkEmbedding = await ChunkEmbedding.fetch_record(
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
        await chunk_metadata.update(session)

        chunk_embedding.chunk_hash = embedded_term.chunk_hash
        chunk_embedding.embedding = embedded_term.embedding
        chunk_embedding.embedding_model = str(self._params.embedding_model)
        chunk_embedding.embedding_date = datetime.now(tz=timezone.utc).isoformat()
        chunk_embedding.embedding_run_id = self.run_id
        await chunk_embedding.update(session)

    async def load(self, session, embedded_terms: List[EmbeddedOntologyTerm]):
        new_term_records: list[EmbeddedOntologyTerm] = []
        for e_term in embedded_terms:
            term: OntologyTerm = e_term.term
            existing_record = await self.__fetch_existing_term(session, term.source_id)

            if existing_record is None:
                await term.submit(
                    session
                )  # submitting terms one-by-one b/c one OWL file may have duplicates
                new_term_records.append(e_term)
                continue

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

                    updated_term = self.__generate_embedded_term(existing_record)
                    await self.__update_embedding(session, updated_term)
                else:
                    self.inc_tx_count(OntologyTerm, ETLOperation.SKIP)
            else:
                self.inc_tx_count(OntologyTerm, ETLOperation.SKIP)

        # bulk submit embeddings
        if len(new_term_records) > 0:
            chunk_metadata = self.__generate_chunk_metadata(new_term_records)
            await ChunkMetadata.submit_many(session, chunk_metadata)

            chunk_embeddings = self.__generate_chunk_embeddings(
                chunk_metadata, new_term_records
            )
            await ChunkEmbedding.submit_many(session, chunk_embeddings)

        return self.create_checkpoint(record=embedded_terms[-1].term)
