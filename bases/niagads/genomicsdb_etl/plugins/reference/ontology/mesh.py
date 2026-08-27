"""Load MeSH Topical Descriptors from the MeSH N-Triples file as Ontology Terms.

This module provides the ETL plugin that parses a MeSH RDF stored as a N-Triple and loads ontology
terms based on the topical descriptors ONLY into the reference ontology term table and their embeddings into the RAG
document tables.  Preferred concepts and their child terms are treated as synonyms for the descriptor.
"""

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
from niagads.rdf_parsers.mesh import MeSHConcept, MeSHDescriptor, MeSHParser, MeSHTerm
from niagads.utils.list import remove_duplicates


@PluginRegistry.register(
    PluginMetadata(
        version="1.0",
        description=(
            f"ETL Plugin to load MeSH topical descriptors from the MeSH N-Triples file into {OntologyTerm.table_name()}."
            f"Loads terms, properties, and embeddings."
        ),
        affected_tables=[ChunkEmbedding, ChunkMetadata, OntologyTerm],
        load_strategy=ETLLoadStrategy.CHUNKED,
        operation=ETLOperation.LOAD,
        is_large_dataset=False,
        parameter_model=BaseOntologyLoaderParams,
    )
)
class MeSHDescriptorLoader(BaseOntologyLoader):
    """Load ontology terms and embeddings from an MeSH N-Triples file.

    The plugin parses MeSH topical descriptors from N-Triples entities,
    establishes synonyms from preferred concepts and their child terms
    and transforms into OntologyTerm objects, creates
    embeddings, and persists new or updated ontology terms and RAG documents.
    """

    _params: BaseOntologyLoaderParams  # type annotation

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
        parser = MeSHParser(
            self._params.file,
            logger=self.logger,
            debug=self._debug,
            verbose=self._verbose,
        )

        # split into "embedding" batch-sized batches to pass to transform
        batch: list[MeSHDescriptor] = []
        for descriptor in parser.extract_topical_descriptors():
            batch.append(descriptor)
            if len(batch) >= self._params.embedding_batch_size:
                yield batch
                batch = []
        if len(batch) > 0:  # residuals
            yield batch

    def __extract_term_labels(self, term: MeSHTerm) -> list[str]:
        """Collect the canonical label plus alternate name variants for a MeSH term.

        Args:
            term: A MeSH term instance containing the primary label and any
                alternate labels or abbreviation metadata.

        Returns:
            A list of labels that can be used as search or synonym strings for the
            term.
        """
        labels: list[str] = [term.label]
        if term.alt_labels:
            labels.extend(term.alt_labels)
        if term.abbreviation:
            labels.append(term.abbreviation)

        return labels

    def __extract_synonyms(self, concept: MeSHConcept):
        """Build the synonym list for a MeSH concept from its preferred term and active child terms.

        Args:
            concept: A MeSH concept whose preferred term and active child terms are
                used to generate searchable synonyms.

        Returns:
            A deduplicated-style list of concept labels and related term labels
            suitable for ontology synonym assignment.
        """
        synonyms: list[str] = [concept.label]
        synonyms.extend(self.__extract_term_labels(concept.preferred_term))
        if concept.terms:
            for term in concept.terms:
                if term.is_active:
                    synonyms.extend(self.__extract_term_labels(term))
        return remove_duplicates(synonyms, ignore_case=True)

    async def transform(self, records: list[MeSHDescriptor]) -> EmbeddedOntologyTerm:
        """Convert parsed MeSH descriptor records to ontology terms and generate embeddings.
        -> term = descriptor, with preferred concepts and their preferred terms assigned as synonyms

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

            if not record.is_active:
                continue  # skip deprecated values

            definition: str = (
                record.preferred_concept.scope_note
                if record.preferred_concept is not None
                else None
            )

            synonyms: list[str] = self.__extract_synonyms(record.preferred_concept)

            term = OntologyTerm(
                namespace="MeSH_descriptor",
                term=record.label,
                label=record.label,
                term_iri=record.iri,
                source_id=f"MESH_{record.id}",
                definition=definition,
                synonyms=synonyms,
                entity_type=EntityTypeIRI.CLASS.name,
            )

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
            f"Calcualted embeddings for {self.__processed_record_count} MeSH terms."
        )

        return embedded_ontology_terms
