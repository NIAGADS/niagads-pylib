"""Load ontology terms and embeddings from an OBO 1.2 file."""

from typing import Any, Dict, Iterator, Optional

from niagads.common.reference.ontologies.types import EntityTypeIRI
from niagads.common.types import ETLOperation
from niagads.database.genomicsdb.schema.ragdoc.chunks import (
    ChunkEmbedding,
    ChunkMetadata,
)
from niagads.database.genomicsdb.schema.reference.ontology import OntologyTerm
from niagads.etl.plugins.metadata import PluginMetadata
from niagads.etl.plugins.registry import PluginRegistry
from niagads.etl.plugins.types import ETLLoadStrategy
from niagads.genomicsdb_etl.plugins.reference.ontology.base import (
    BaseOntologyLoader,
    BaseOntologyLoaderParams,
    EmbeddedOntologyTerm,
)
from niagads.utils.list import remove_duplicates
from niagads.utils.string import regex_extract
from niagads.utils.sys import read_open_ctx
from pydantic import BaseModel, Field

_QUOTED_VALUE_PATTERN = r'^"((?:\\.|[^"\\])*)"'


class TermRecord(BaseModel):
    """A term record supported by the NIAGADS OBO source file."""

    source_id: str = Field(description="OBO term identifier")
    term: str = Field(description="OBO term name")
    definition: Optional[str] = Field(default=None, description="Term definition")
    synonyms: list[str] = Field(default_factory=list, description="Term synonyms")
    is_a: list[str] = Field(default_factory=list, description="Parent term IDs")

    @classmethod
    def from_obo_block(cls, block: list[str]):
        """Create a typed term record from an OBO ``[Term]`` block."""
        if not block or block[0] != "[Term]":
            return None

        source_id = None
        term = None
        definition = None
        synonyms = []
        is_a = []

        for line in block[1:]:
            if not line or line.startswith("!") or ":" not in line:
                continue

            field, value = line.split(":", 1)
            value = value.strip()
            if field == "id":
                source_id = value
            elif field == "name":
                term = value
            elif field == "def":
                definition = regex_extract(_QUOTED_VALUE_PATTERN, value) or value
            elif field == "synonym":
                synonym = regex_extract(_QUOTED_VALUE_PATTERN, value) or value
                synonyms.append(synonym)
            elif field == "is_a":
                is_a.append(value.split("!", 1)[0].strip())

        return cls(
            source_id=source_id,
            term=term,
            definition=definition,
            synonyms=remove_duplicates(synonyms, ignore_case=True),
            is_a=is_a,
        )


class OBOLoaderParams(BaseOntologyLoaderParams):
    """Configuration parameters for loading ontology terms from an OBO file."""

    namespace: str = Field(
        default="NIAGADS",
        description="Ontology namespace assigned to loaded terms",
    )


@PluginRegistry.register(
    PluginMetadata(
        version="1.0",
        description=(
            f"ETL Plugin to load ontology terms from an OBO file into "
            f"{OntologyTerm.table_name()}. Loads terms and embeddings."
        ),
        affected_tables=[ChunkEmbedding, ChunkMetadata, OntologyTerm],
        load_strategy=ETLLoadStrategy.CHUNKED,
        operation=ETLOperation.LOAD,
        is_large_dataset=False,
        parameter_model=OBOLoaderParams,
    )
)
class OBOTermLoader(BaseOntologyLoader):
    """Load new ontology terms and embeddings from an OBO 1.2 file.

    Existing records are identified by the exact pair of ``term`` and
    ``source_id``. Existing records are skipped; their term metadata and
    embeddings are not updated.
    """

    _params: OBOLoaderParams

    def __init__(
        self,
        params: Dict[str, Any],
        name: Optional[str] = None,
        log_path: str = None,
        debug: bool = False,
        verbose: bool = False,
    ):
        super().__init__(params, name, log_path, debug, verbose)
        self.__processed_record_count = 0

    @staticmethod
    def __extract_terms(file: str) -> Iterator[TermRecord]:
        """Yield typed ontology records from OBO ``[Term]`` stanzas."""
        block = []

        with read_open_ctx(file) as file_handle:
            for raw_line in file_handle:
                line = raw_line.strip()
                if not line:
                    continue

                if line == "[Term]":
                    if block:
                        record = TermRecord.from_obo_block(block)
                        if record is not None:
                            yield record
                    block = [line]

                elif block and not line.startswith("!"):
                    block.append(line)

        if block:
            record = TermRecord.from_obo_block(block)
            if record is not None:
                yield record

    def extract(self) -> Iterator[list[TermRecord]]:
        """Extract OBO terms in embedding-sized batches."""
        batch = []
        for term in self.__extract_terms(self._params.file):
            batch.append(term)
            if len(batch) >= self._params.embedding_batch_size:
                yield batch
                batch = []
        if batch:
            yield batch

    async def transform(self, records: list[TermRecord]) -> list[EmbeddedOntologyTerm]:
        """Create ontology records and embeddings for one extracted batch."""

        embedded_terms: list[EmbeddedOntologyTerm] = []
        text = []
        for record in records:
            term = OntologyTerm(
                term_iri=(
                    "http://purl.obolibrary.org/obo/"
                    f"{record.source_id.replace(':', '_')}"
                ),
                entity_type=str(EntityTypeIRI.CLASS),
                source_id=record.source_id,
                term=record.term,
                label=record.term,
                definition=record.definition,
                namespace=self._params.namespace,
                synonyms=record.synonyms or None,
            )
            if term.synonyms:
                term.synonym_list_str = " // ".join(term.synonyms)
            if self.is_etl_run:
                term.run_id = self.run_id
                term.external_database_id = self.external_database_id

            embedded_term = self._generate_chunk_text(term)
            embedded_terms.append(embedded_term)
            text.append(embedded_term.chunk_text)

        embeddings = self._embedding_generator.generate(text, as_list=False)

        for index, embedded_term in enumerate(embedded_terms):
            embedded_term.embedding = embeddings[index].tolist()

        self.__processed_record_count += len(embedded_terms)
        self.logger.info(
            f"Calculated embeddings for {self.__processed_record_count} ontology terms."
        )
        return embedded_terms

    async def load(self, session, embedded_terms: list[EmbeddedOntologyTerm]):
        """Insert only terms not already present by exact term/source ID match."""
        new_terms = []
        seen = set()
        for embedded_term in embedded_terms:
            term = embedded_term.term
            key = (self.external_database_id, term.source_id, term.term)
            if key in seen or await OntologyTerm.record_exists(
                session,
                {
                    "namespace": term.namespace,
                    "source_id": term.source_id,
                    "term": term.term,
                },
            ):
                self.inc_tx_count(OntologyTerm, ETLOperation.SKIP)
                continue

            seen.add(key)
            await term.submit(session)
            new_terms.append(embedded_term)

        if new_terms:
            metadata = self._generate_chunk_metadata(new_terms)
            await ChunkMetadata.submit_many(session, metadata)
            embeddings = self._generate_chunk_embeddings(metadata, new_terms)
            await ChunkEmbedding.submit_many(session, embeddings)

        return self.create_checkpoint(record=embedded_terms[-1].term)

    def get_record_id(self, record: OntologyTerm) -> str:
        """Return the source identifier used for checkpointing."""
        return record.source_id
