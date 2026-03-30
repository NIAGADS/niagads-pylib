"""
Gene Structure Loader Plugin
- Parse Ensembl GFF3 files and load gene, transcript, and exon records into gene structure tables.
"""

from typing import Any, Dict, Iterator, List, Optional

from niagads.common.types import ETLOperation
from niagads.database.genomicsdb.schema.gene.structure import (
    GeneModel,
    TranscriptModel,
    ExonModel,
)
from niagads.common.gene.models.structure import GeneModel as Gene
from niagads.database.genomicsdb.schema.reference.externaldb import ExternalDatabase
from niagads.etl.plugins.base import AbstractBasePlugin
from niagads.etl.plugins.metadata import PluginMetadata
from niagads.etl.plugins.parameters import BasePluginParams, PathValidatorMixin
from niagads.etl.plugins.registry import PluginRegistry
from niagads.etl.plugins.types import ETLLoadStrategy
from niagads.genomicsdb_etl.plugins.common.mixins.parameters import (
    ExternalDatabaseRefMixin,
)
from niagads.flatfile.formats.gff3 import EnsemblGFF3Parser
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

    @property
    def external_database_id(self):
        return self.__external_database.external_database_id

    async def on_run_start(self, session):
        # validate the xdbref against the database
        self.__external_database: ExternalDatabase = (
            await self._params.fetch_xdbref(session) if self.is_etl_run else None
        )

        self.logger.debug(
            f"external_database_id = {self.__external_database.external_database_id}"
        )

    def get_record_id(self, record: GeneModel) -> str:
        return record.source_id

    def extract(self) -> Iterator:
        """
        Extract gene structures from Ensembl GFF3 file.

        Uses EnsemblGFF3Parser to parse the GFF3 file and yields gene records
        with nested transcript and exon data as Pydantic models.

        Yields:
            GeneModel: Pydantic gene model with nested transcripts and exons
        """
        parser = EnsemblGFF3Parser(
            file=self._params.file,
            debug=self._debug,
            verbose=self._verbose,
        )

        for gene_model in parser:
            yield gene_model

    def transform(self, records: List[Gene]):
        """
        Transform gene models from GFF3 parser into ORM model instances.

        Yields each gene with its transcripts and exons separately, maintaining
        foreign key dependencies while allowing the base plugin to handle batching.
        Each yield contains the complete data for one gene: the gene itself, its
        transcripts, and their exons.

        Args:
            records: Iterable of Pydantic GeneModel instances from extract()

        Yields:
            For each gene:
            - List with [GeneModel ORM]
            - List with all TranscriptModel ORM instances for that gene
            - List with all ExonModel ORM instances for that gene's transcripts
        """
        for gene_model in records:
            # Create GeneModel ORM instance
            gene_orm = GeneModel(
                source_id=gene_model.id,
                gene_symbol=gene_model.symbol,
                gene_name=gene_model.description,
                gene_type=gene_model.biotype,
                chromosome=gene_model.location.chromosome,
                genomic_region=gene_model.location,
                external_database_id=self.external_database_id,
                run_id=self.run_id,
            )
            # Yield gene first
            yield gene_orm

            # Collect and yield transcripts for this gene
            transcripts = []
            exons = []

            for transcript_model in gene_model.transcripts:
                transcript_orm = TranscriptModel(
                    source_id=transcript_model.id,
                    gene_id=gene_model.id,
                    chromosome=transcript_model.location.chromosome,
                    genomic_region=transcript_model.location,
                    external_database_id=self.external_database_id,
                    run_id=self.run_id,
                )
                transcripts.append(transcript_orm)

                # Collect exons for this transcript
                for exon_model in transcript_model.exons:
                    exon_orm = ExonModel(
                        source_id=exon_model.id,
                        gene_id=gene_model.id,
                        transcript_id=transcript_model.id,
                        chromosome=exon_model.location.chromosome,
                        genomic_region=exon_model.location,
                        external_database_id=self.external_database_id,
                        run_id=self.run_id,
                    )
                    exons.append(exon_orm)

            # Yield transcripts for this gene
            if transcripts:
                yield transcripts

            # Yield exons for this gene
            if exons:
                yield exons

    async def load(self, session, gene_models: list[GeneModel]): ...

    # TODO - ontology term look up of biotype (in load)
    # TODO - bin_index assignation (in load?)
    # TODO - update gene and transcript ids with pks
