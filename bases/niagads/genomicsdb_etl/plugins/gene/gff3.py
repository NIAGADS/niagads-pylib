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

    def extract(self) -> Iterator[dict]:
        """
        Extract gene structures from Ensembl GFF3 file.

        Yields batches of gene records (with nested transcript and exon data)
        as dictionaries, sized according to commit_after parameter.

        Returns:
            Iterator[dict]: Batches of gene records with nested structure.
        """

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
