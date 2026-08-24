from datetime import datetime
from typing import Any, Dict, List, Optional

from niagads.common.types import ETLOperation
from niagads.database.genomicsdb.schema.ragdoc.chunks import (
    ChunkEmbedding,
    ChunkMetadata,
)
from niagads.database.genomicsdb.schema.ragdoc.types import RAGDocType
from niagads.database.genomicsdb.schema.reference.externaldb import ExternalDatabase
from niagads.database.genomicsdb.schema.reference.ontology import OntologyTerm
from niagads.etl.plugins.base import AbstractBasePlugin
from niagads.etl.plugins.mixins import (
    EmbeddingGeneratorContextMixin,
    ExternalDatabaseContextMixin,
)
from niagads.etl.plugins.parameters import (
    BasePluginParams,
    EmbeddingParameterMixin,
    PathValidatorMixin,
)
from niagads.genomicsdb_etl.plugins.common.mixins.parameters import (
    ExternalDatabaseRefMixin,
)
from pydantic import BaseModel, Field
from sqlalchemy.exc import NoResultFound


class EmbeddedOntologyTerm(BaseModel, arbitrary_types_allowed=True):
    """An ontology term together with the text and embedding generated for it.

    Attributes:
        term: The ontology term represented by this object.
        chunk_text: Text generated from the term for embedding and retrieval.
        chunk_hash: Hash of ``chunk_text``.
        embedding: Optional embedding vector; populated during transformation.
    """

    term: OntologyTerm
    chunk_text: str
    chunk_hash: bytes
    embedding: Optional[list] = None  # so it can be set in batch


# FIXME - just use ontologygraphtriple
class Triple(BaseModel):
    """An RDF relationship represented by subject, predicate, and object IRIs."""

    subject: str
    predicate: str
    object: str

    def __str__(self):
        """Return the triple as an arrow-delimited string."""
        return f"{str(self.subject)} -> {str(self.predicate)} -> {str(self.object)}"


class BaseOntologyLoaderParams(
    BasePluginParams,
    PathValidatorMixin,
    ExternalDatabaseRefMixin,
    EmbeddingParameterMixin,
):
    """shared parameters for loading ontology terms."""

    file: str = Field(..., description="full path to ontology file")
    update_existing: Optional[bool] = Field(
        default=False,
        description="if term already exists in the table, attempts to update defintion and synonyms if necessary; if set to false, just skips existing terms",
    )
    validate_file_exists = PathValidatorMixin.validator("file")


class BaseOntologyLoader(
    AbstractBasePlugin, EmbeddingGeneratorContextMixin, ExternalDatabaseContextMixin
):
    """
    Foundational class for plugins loading ontologies.

    Overloads `on_run_start` to handle the external database referencel lookup.

    Provides helper functions for embedding.
    """

    _params: BaseOntologyLoaderParams

    def __init__(
        self,
        params: Dict[str, Any],
        name: Optional[str] = None,
        log_path: str = None,
        debug: bool = False,
        verbose: bool = False,
    ):
        super().__init__(params, name, log_path, debug, verbose)
        self.__external_database: ExternalDatabase = None

    @property
    def external_database_id(self):
        return self.__external_database.external_database_id

    @property
    def external_database_key(self):
        return self.__external_database.database_key

    async def on_run_start(self, session):
        """Initialize database and embedding contexts before the run.

        Args:
            session: Database session used to initialize plugin context.
        """
        await ExternalDatabaseContextMixin.on_run_start(self, session)
        await EmbeddingGeneratorContextMixin.on_run_start(self, session)

        # get the table catalog reference for the OntologyTerm table
        await self.set_table_ref(session, OntologyTerm)

    def get_record_id(self, record: OntologyTerm) -> str:
        """Return the source identifier for an ontology term.

        Args:
            record: Ontology term whose identifier should be returned.

        Returns:
            str: The term's source ID.
        """
        return record.source_id

    async def _lookup_term(self, session, source_id: str) -> Optional[OntologyTerm]:
        """Fetch an ontology term by source ID.

        Args:
            session: Database session used for the query.
            source_id: Source identifier of the ontology term.

        Returns:
            Optional[OntologyTerm]: The matching term, or None if it does not
                exist.
        """
        try:
            return await OntologyTerm.fetch_record(
                session, filters={"source_id": source_id}
            )
        except NoResultFound:
            return None

    def _generate_chunk_text(self, term: OntologyTerm) -> EmbeddedOntologyTerm:
        """Create searchable chunk text for an ontology term.

        Args:
            term: Ontology term from which chunk text should be generated.

        Returns:
            EmbeddedOntologyTerm: Term and its generated text and hash.
        """
        chunk_text: str = (
            f"Term: {term.term}\nLabel: {term.label}"
            f"\nCURIE: {term.source_id}\nDefinition: {term.definition}"
        )
        if term.synonyms:
            for s in term.synonyms:
                chunk_text += f"\nSynonym: {s}"

        if term.namespace:
            chunk_text += f"\nNamespace: {term.namespace}"

        if self._verbose:
            self.logger.debug(f"Chunk Text: {chunk_text}")

        return EmbeddedOntologyTerm(
            term=term,
            chunk_text=chunk_text,
            chunk_hash=self._embedding_generator.hash_text(chunk_text),
        )

    def _generate_embedded_term(self, term: OntologyTerm) -> EmbeddedOntologyTerm:
        """Generate an embedding for a single ontology term.

        Args:
            term: Ontology term to embed.

        Returns:
            EmbeddedOntologyTerm: Term with generated chunk text, hash, and
                embedding.
        """
        embedded_term = self._generate_chunk_text(term)
        embedded_term.embedding = self._embedding_generator.generate(
            embedded_term.chunk_text, as_list=True
        )
        return embedded_term

    def _generate_chunk_metadata(self, term_records: list[EmbeddedOntologyTerm]):
        """Create RAG chunk metadata for embedded ontology terms.

        Args:
            term_records: Embedded ontology terms for which metadata is created.

        Returns:
            list[ChunkMetadata]: Metadata records corresponding to the terms.
        """
        return [
            ChunkMetadata(
                table_id=self._table_ref.table_id,
                row_id=embedded_term.term.ontology_term_id,
                document_type=str(RAGDocType.ONTOLOGY),
                document_hash=embedded_term.chunk_hash,
                chunk_hash=embedded_term.chunk_hash,
                chunk_text=embedded_term.chunk_text,
                run_id=self.run_id,
            )
            for embedded_term in term_records
        ]

    def _generate_chunk_embeddings(
        self, metadata: list[ChunkMetadata], term_records: list[EmbeddedOntologyTerm]
    ):
        """Create RAG embedding records from chunk metadata and terms.

        Args:
            metadata: Chunk metadata records associated with the terms.
            term_records: Embedded ontology terms containing embedding vectors.

        Returns:
            list[ChunkEmbedding]: Embedding records ready for persistence.
        """
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

    async def _update_embedding(self, session, embedded_term: EmbeddedOntologyTerm):
        """Update the stored RAG records for an existing ontology term.

        Args:
            session: Database session used for fetching and updating records.
            embedded_term: Updated term text and embedding to persist.
        """

        # pull records to update from the database
        chunk_metadata: ChunkMetadata = await ChunkMetadata.fetch_record(
            session,
            filters={
                "table_id": self._table_ref.table_id,
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
        chunk_embedding.embedding_date = datetime.now().isoformat()
        chunk_embedding.embedding_run_id = self.run_id
        await chunk_embedding.update(session)

    async def load(self, session, embedded_terms: List[EmbeddedOntologyTerm]):
        """Persist new terms and embeddings, and optionally update existing terms.

        Args:
            session: Database session used for persistence.
            embedded_terms: Transformed ontology terms and their embeddings.

        Returns:
            The checkpoint created from the final processed ontology term.
        """
        new_term_records: list[EmbeddedOntologyTerm] = []
        for e_term in embedded_terms:
            term: OntologyTerm = e_term.term
            existing_record = await self._lookup_term(session, term.source_id)

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
                    namespace=self._external_database.database_key,
                )

                updated_synonyms = await existing_record.resolve_synonyms(
                    session, term.synonyms
                )

                if updated_definitions or updated_synonyms:
                    self.inc_tx_count(OntologyTerm, ETLOperation.UPDATE)

                    # if the term was defined in the current namespace, update
                    # the external db reference as well
                    if await existing_record.in_namespace(
                        session, self._external_database.database_key
                    ):
                        existing_record.external_database_id = self.external_database_id
                        await existing_record.update(session)

                    updated_term = self._generate_embedded_term(existing_record)
                    await self._update_embedding(session, updated_term)
                else:
                    self.inc_tx_count(OntologyTerm, ETLOperation.SKIP)
            else:
                self.inc_tx_count(OntologyTerm, ETLOperation.SKIP)

        # bulk submit embeddings
        if len(new_term_records) > 0:
            chunk_metadata = self._generate_chunk_metadata(new_term_records)
            await ChunkMetadata.submit_many(session, chunk_metadata)

            chunk_embeddings = self._generate_chunk_embeddings(
                chunk_metadata, new_term_records
            )
            await ChunkEmbedding.submit_many(session, chunk_embeddings)

        return self.create_checkpoint(record=embedded_terms[-1].term)
