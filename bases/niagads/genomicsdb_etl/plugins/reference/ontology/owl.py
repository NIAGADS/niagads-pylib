"""Load ontology terms and embeddings from OWL files.

This module provides the ETL plugin that parses an OWL file and loads ontology
terms into the reference ontology term table and their embeddings into the RAG
document tables.
"""

from typing import Any, Dict, Iterator, Optional

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
from niagads.rdf_parsers import OWLParser
from pydantic import Field


class OWLLoaderParams(BaseOntologyLoaderParams):
    """Configuration parameters for loading ontology terms from an OWL file."""

    curie_prefix: Optional[str] = Field(
        default=None,
        description="prefix for curie for ontologies that don't include the namespace in "
        "the curie; e.g., EDAM -> topic:001 => EDAM:topic_001",
    )


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
        parameter_model=OWLLoaderParams,
    )
)
class OntologyTermLoader(BaseOntologyLoader):
    """Load ontology terms and embeddings from an OWL file.

    The plugin parses OWL entities, optionally prefixes their CURIEs, creates
    embeddings, and persists new or updated ontology terms and RAG documents.
    """

    _params: OWLLoaderParams  # type annotation

    def __init__(
        self,
        params: Dict[str, Any],
        name: Optional[str] = None,
        log_path: str = None,
        debug: bool = False,
        verbose: bool = False,
    ):
        """Initialize the ontology term loader.

        Args:
            params: Plugin configuration parameters.
            name: Optional plugin name.
            log_path: Optional path for plugin log output.
            debug: If True, enable debug logging and behavior.
            verbose: If True, enable verbose logging.
        """
        super().__init__(params, name, log_path, debug, verbose)
        self.__processed_record_count = 0

    def extract(self) -> Iterator[Any]:
        """Extract ontology terms from the configured OWL file in batches.

        Returns:
            Iterator[Any]: Batches of parsed ontology term dictionaries sized
                according to the configured embedding batch size.
        """
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

    async def transform(self, records: list[dict]) -> EmbeddedOntologyTerm:
        """Convert parsed OWL records to ontology terms and generate embeddings.

        Args:
            records: Batch of dictionaries representing parsed OWL entities.

        Returns:
            list[EmbeddedOntologyTerm]: Transformed ontology terms with
                embeddings.

        Raises:
            RuntimeError: If ``records`` is None or an empty list.
        """
        if records is None or (isinstance(records, list) and len(records) == 0):
            raise RuntimeError(
                "No records provided to transform(). At least one record is required."
            )

        embedded_ontology_terms = []
        text = []
        for record in records:
            curie: str = record.pop("curie")
            if self._params.curie_prefix is not None:
                curie = f"{self._params.curie_prefix}:{curie.replace(':', '_')}"
            record["source_id"] = curie

            term: OntologyTerm = OntologyTerm(**record)

            # for text searches
            if term.synonyms is not None:
                term.synonym_list_str = " // ".join(term.synonyms)

            if term.label is None:
                term.label = term.term.replace("_", " ")

            if self.is_etl_run:  # catch dry runs
                term.run_id = self.run_id
                term.external_database_id = self.external_database_id

            if self._verbose:
                self.logger.debug(f"Term: {term.model_dump()}")

            embedded_term = self._generate_chunk_text(term)
            embedded_ontology_terms.append(embedded_term)
            text.append(embedded_term.chunk_text)

        embeddings = self._embedding_generator.generate(text, as_list=False)

        eterm: EmbeddedOntologyTerm
        for index, eterm in enumerate(embedded_ontology_terms):
            eterm.embedding = embeddings[index].tolist()

        self.__processed_record_count += self._params.embedding_batch_size
        self.logger.info(
            f"Calcualted embeddings for {self.__processed_record_count} ontology terms."
        )

        return embedded_ontology_terms
