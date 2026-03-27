"""
Gene Structure Loader Plugin
- Parse Ensembl GFF3 files and load gene, transcript, and exon records into gene structure tables.
"""

from typing import Any, Dict, Iterator, Optional

from niagads.common.types import ETLOperation
from niagads.database.genomicsdb.schema.gene.structure import (
    GeneModel,
    TranscriptModel,
    ExonModel,
)
from niagads.etl.plugins.base import AbstractBasePlugin
from niagads.etl.plugins.metadata import PluginMetadata
from niagads.etl.plugins.parameters import BasePluginParams, PathValidatorMixin
from niagads.etl.plugins.registry import PluginRegistry
from niagads.etl.plugins.types import ETLLoadStrategy
from niagads.genomicsdb_etl.plugins.common.mixins.parameters import (
    ExternalDatabaseRefMixin,
)
from pydantic import Field


class EnsemblGFF3LoaderParams(
    BasePluginParams, PathValidatorMixin, ExternalDatabaseRefMixin
):
    """Parameters for Ensembl GFF3 gene structure loader plugin."""

    file: str = Field(..., description="full path to Ensembl GFF3 file")

    validate_file_exists = PathValidatorMixin.validator("file", is_dir=False)


metadata = PluginMetadata(
    version="1.0",
    description=(
        "ETL Plugin to load gene structures (genes, transcripts, exons) from an Ensembl GFF3 file"
    ),
    affected_tables=[ExonModel, TranscriptModel, GeneModel],
    load_strategy=ETLLoadStrategy.CHUNKED,
    operation=ETLOperation.INSERT,
    is_large_dataset=False,
    parameter_model=EnsemblGFF3LoaderParams,
)


@PluginRegistry.register(metadata)
class EnsemblGFF3Loader(AbstractBasePlugin):
    """
    ETL plugin for loading gene structures from an Ensembl GFF3 file.

    Parses gene, transcript, and exon features from a GFF3 file and loads them
    into the gene, transcript, and exon tables in the GenomicsDB database.
    """

    _params: EnsemblGFF3LoaderParams  # type annotation

    def __init__(
        self,
        params: Dict[str, Any],
        name: Optional[str] = None,
        debug: bool = False,
        verbose: bool = False,
    ):
        super().__init__(params, name, debug, verbose)

    def get_record_id(self, record: GeneModel) -> str:
        return record.source_id

    def __open_text_file(self, path: str) -> io.TextIOBase:
        """Open plain text or .gz GFF3 file as a text stream."""
        if path.endswith(".gz"):
            return io.TextIOWrapper(gzip.open(path, "rb"), encoding="utf-8")
        return open(path, "r", encoding="utf-8")

    def __strip_prefix(self, value: Optional[str]) -> Optional[str]:
        """Return the part after the first colon (e.g., 'gene:ENSG...' -> 'ENSG...')."""
        return None if value is None else value.split(":", 1)[-1]

    def __parse_attributes(self, attributes: str) -> Dict[str, Any]:
        """
        Parse GFF3 attributes field into a dictionary.

        Args:
            attributes: Semicolon-separated key=value pairs.

        Returns:
            Dictionary of parsed attributes.
        """
        attrs = {}
        for pair in attributes.split(";"):
            if not pair.strip():
                continue
            key, value = pair.strip().split("=", 1)
            # GFF3 spec: comma-separated values become lists
            if "," in value:
                attrs[key] = value.split(",")
            else:
                attrs[key] = value
        return attrs

    def extract(self) -> Iterator[dict]:
        """
        Extract gene structures from Ensembl GFF3 file.

        Yields batches of gene records (with nested transcript and exon data)
        as dictionaries, sized according to commit_after parameter.

        Returns:
            Iterator[dict]: Batches of gene records with nested structure.
        """
        current_gene: Optional[Dict[str, Any]] = None
        current_transcript: Optional[Dict[str, Any]] = None
        batch: list[dict] = []

        with self.__open_text_file(self._params.file) as fh:
            for line in fh:
                # Skip comments and blank lines
                if not line.strip() or line.startswith("#"):
                    continue

                fields = line.rstrip("\n").split("\t")
                if len(fields) != 9:
                    self.logger.warning(
                        f"Skipping malformed line (expected 9 fields): {line[:80]}"
                    )
                    continue

                (
                    seqid,
                    source,
                    feature_type,
                    start,
                    end,
                    score,
                    strand,
                    phase,
                    attributes,
                ) = fields

                attrs = self.__parse_attributes(attributes)
                feature_id = self.__strip_prefix(attrs.get("ID"))
                parent_id = self.__strip_prefix(attrs.get("Parent"))

                # Process gene features
                if feature_type == "gene":
                    # Emit previous gene if exists
                    if current_gene is not None:
                        batch.append(current_gene)
                        if len(batch) >= self._commit_after:
                            yield batch
                            batch = []

                    # Extract gene attributes
                    gene_symbol = attrs.get("gene_name", feature_id)
                    if isinstance(gene_symbol, list):
                        gene_symbol = gene_symbol[0]

                    current_gene = {
                        "source_id": feature_id,
                        "gene_symbol": gene_symbol or feature_id,
                        "gene_name": attrs.get(
                            "description", gene_symbol or feature_id
                        ),
                        "gene_type": attrs.get("biotype", "unknown"),
                        "chromosome": seqid,
                        "start": int(start),
                        "end": int(end),
                        "strand": strand,
                        "transcripts": [],
                    }
                    current_transcript = None

                    if self._verbose:
                        self.logger.debug(f"Parsed gene: {feature_id}")

                # Process transcript features
                elif feature_type == "transcript" and current_gene is not None:
                    current_transcript = {
                        "source_id": feature_id,
                        "chromosome": seqid,
                        "start": int(start),
                        "end": int(end),
                        "strand": strand,
                        "exons": [],
                    }
                    current_gene["transcripts"].append(current_transcript)

                    if self._verbose:
                        self.logger.debug(f"  Parsed transcript: {feature_id}")

                # Process exon features (linked to transcript)
                elif feature_type == "exon" and current_transcript is not None:
                    exon = {
                        "source_id": feature_id,
                        "chromosome": seqid,
                        "start": int(start),
                        "end": int(end),
                        "strand": strand,
                    }
                    current_transcript["exons"].append(exon)

                    if self._verbose:
                        self.logger.debug(f"    Parsed exon: {feature_id}")

            # Emit the final gene
            if current_gene is not None:
                batch.append(current_gene)

        # Yield any remaining genes in batch
        if batch:
            yield batch

    def transform(self, records: list[dict]) -> list[GeneModel]:

        # TODO: Implement transformation logic
        # Should:
        # 1. Convert gene records to GeneModel objects
        # 2. Convert transcript records to TranscriptModel objects
        # 3. Convert exon records to ExonModel objects
        # 4. Link transcripts to genes via gene_id
        # 5. Link exons to transcripts and genes via foreign keys
        # 6. Set run_id and external_database_id on all records
        # 7. Validate data against schema constraints
        raise NotImplementedError("Record transformation logic to be implemented")

    async def load(self, session, gene_models: list[GeneModel]):

        # TODO: Implement load logic
        # Should:
        # 1. Check if genes already exist and handle according to skip_existing parameter
        # 2. Submit new GeneModel records
        # 3. Extract TranscriptModel records from genes and submit
        # 4. Extract ExonModel records from transcripts and submit
        # 5. Track transaction counts (INSERT/UPDATE/SKIP) for each table
        # 6. Return checkpoint based on last processed gene for resumption
        raise NotImplementedError("Load logic to be implemented")
