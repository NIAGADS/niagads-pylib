"""
Gene Structure Loader Plugin
- Parse Ensembl GFF3 files and load gene, transcript, and exon records into gene structure tables.
"""

from enum import auto
from typing import Any, Dict, Iterator, List, Optional

from sqlalchemy import Enum

from niagads.common.models.types import Range
from niagads.common.types import ETLOperation
from niagads.database.genomicsdb.schema.gene.structure import (
    GeneModel,
    TranscriptModel,
    ExonModel,
)
from niagads.common.gene.models.structure import GeneModel as GFF3GeneRecord
from niagads.database.genomicsdb.schema.reference.externaldb import ExternalDatabase
from niagads.database.genomicsdb.schema.reference.interval_bin import IntervalBin
from niagads.database.genomicsdb.schema.reference.ontology import OntologyTerm
from niagads.etl.plugins.base import AbstractBasePlugin
from niagads.etl.plugins.metadata import PluginMetadata
from niagads.etl.plugins.parameters import BasePluginParams, PathValidatorMixin
from niagads.etl.plugins.registry import PluginRegistry
from niagads.etl.plugins.types import ETLLoadStrategy
from niagads.genomicsdb_etl.plugins.common.mixins.parameters import (
    ExternalDatabaseRefMixin,
)
from niagads.flatfile.formats.gff3 import EnsemblGFF3Parser
from pydantic import BaseModel, Field

from niagads.genome_reference.human import HumanGenome


class EnsemblGFF3LoaderParams(
    BasePluginParams, PathValidatorMixin, ExternalDatabaseRefMixin
):
    """Parameters for Ensembl GFF3 gene structure loader plugin."""

    file: str = Field(..., description="full path to Ensembl GFF3 file")
    so_xdbref: str = Field(
        ...,
        description="external database reference for the sequence ontology `SO|version'",
    )

    validate_file_exists = PathValidatorMixin.validator("file")


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


class FeatureType(Enum):
    GENE = auto()
    TRANSCRIPT = auto()
    EXON = auto()


class FeatureModel(BaseModel):
    feature_type: str
    id: str
    gene_symbol: Optional[str] = None
    gene_name: Optional[str] = None
    biotype: Optional[str] = None
    parent_id: Optional[str] = None
    chromosome: HumanGenome
    genomic_region: Range


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
        log_path: str = None,
        debug: bool = False,
        verbose: bool = False,
    ):
        super().__init__(params, name, log_path, debug, verbose)
        # Cache for gene primary keys to avoid redundant database queries
        self.__gene_pk_ref = {}
        # Cache for transcript primary keys to maintain relationships with genes
        self.__transcript_pk_ref = {}
        # Mapping of transcript primary keys to their parent gene primary keys
        self.__transcript2gene_ref = {}
        # References for ontology terms
        self.__ontology_term_ref = {}
        # External database ID for sequence ontology
        self.__so_external_database_id = None
        # External database instance
        self.__external_database: ExternalDatabase = None

    @property
    def external_database_id(self):
        return self.__external_database.external_database_id

    async def on_run_start(self, session):
        if self.is_etl_run:
            # validate the xdbref against the database
            self.__external_database = await self._params.fetch_xdbref(session)

            self.logger.debug(
                f"external_database_id = {self.__external_database.external_database_id}"
            )

            # validate and fetch sequence ontology external database ref
            so_xbdref_param = ExternalDatabaseRefMixin(xdbref=self._params.so_xdbref)
            so_xdbref: ExternalDatabase = await so_xbdref_param.fetch_xdbref(session)
            self.__so_external_database_id = so_xdbref.external_database_id

    def get_record_id(self, record: GeneModel) -> str:
        return record.source_id

    def extract(self) -> Iterator[GFF3GeneRecord]:
        """
        Extract gene structures from Ensembl GFF3 file.

        Uses EnsemblGFF3Parser to parse the GFF3 file and yields gene records
        with nested transcript and exon data as Pydantic models.

        Yields:
            GeneModel: Pydantic gene model with nested transcripts and exons
        """
        parser = EnsemblGFF3Parser(
            file=self._params.file,
            logger=self.logger,
            debug=self._debug,
            verbose=self._verbose,
        )

        for gene_model in parser:
            yield gene_model

    def transform(self, records: List[GFF3GeneRecord]):
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
            # NOTE: gene_type_id will need to be updated w/ontology_term_id
            # in load
            gene = FeatureModel(
                feature_type=FeatureType.GENE,
                id=gene_model.id,
                gene_symbol=gene_model.symbol,
                gene_name=gene_model.description,
                gene_type_id=gene_model.biotype,
                chromosome=gene_model.location.chromosome,
                genomic_region=gene_model.location,
            )

            # Yield gene first
            yield gene

            # Collect and yield transcripts for this gene
            transcripts = []
            exons = []

            # NOTE: gene_id, transcript_id FKs will need to updated to PKs
            # in load
            for transcript_model in gene_model.transcripts:
                transcripts.append(
                    FeatureModel(
                        feature_type=FeatureType.TRANSCRIPT,
                        id=transcript_model.id,
                        parent_id=gene_model.id,
                        chromosome=transcript_model.location.chromosome,
                        genomic_region=transcript_model.location,
                    )
                )

                # Collect exons for this transcript
                for exon_model in transcript_model.exons:
                    exons.append(
                        FeatureModel(
                            feature_type=FeatureType.EXON,
                            id=exon_model.id,
                            parent_id=transcript_model.id,
                            chromosome=exon_model.location.chromosome,
                            genomic_region=exon_model.location,
                        )
                    )

            # Yield transcripts for this gene
            if transcripts:
                yield transcripts

            # Yield exons for this gene
            if exons:
                yield exons

    async def __lookup_gene_biotype(self, session, biotype: str):
        """find ontology_term_id matching gene biotype"""
        try:
            ontology_term_id = self.__ontology_term_ref[biotype]
        except:
            ontology_term_id = await OntologyTerm.find_primary_key(
                session,
                filters={
                    "external_database_id": self.__so_external_database_id,
                    "term": biotype,
                },
            )
            self.__ontology_term_ref[biotype] = ontology_term_id
        return ontology_term_id

    async def load(self, session, records: List[FeatureModel]):
        for feature_model in records:
            bin_index = await IntervalBin.find_bin_index(feature_model.genomic_region)
            if feature_model.feature_type == FeatureType.GENE:
                gene_type_id = await self.__lookup_gene_biotype(
                    session, feature_model.biotype
                )
                gene = GeneModel(
                    source_id=feature_model.id,
                    gene_symbol=feature_model.gene_symbol,
                    gene_name=feature_model.gene_name,
                    gene_type_id=gene_type_id,
                    chromosome=feature_model.chromosome,
                    genomic_region=feature_model.genomic_region,
                    bin_index=bin_index,
                    external_databse_id=self.external_database_id,
                    run_id=self.run_id,
                )
                gene_pk = gene.submit(session)
                self.__gene_pk_ref[feature_model.id] = gene_pk

            if feature_model.feature_type == FeatureType.TRANSCRIPT:
                parent_gene_pk = self.__gene_pk_ref[feature_model.parent_id]
                transcript = TranscriptModel(
                    source_id=feature_model.id,
                    gene_id=parent_gene_pk,
                    chromosome=feature_model.chromosome,
                    genomic_region=feature_model.genomic_region,
                    bin_index=bin_index,
                    external_databse_id=self.external_database_id,
                    run_id=self.run_id,
                )
                transcript_pk = transcript.submit(session)
                self.__transcript_pk_ref[feature_model.id] = transcript_pk
                self.__transcript2gene_ref[transcript_pk] = parent_gene_pk

            if feature_model.feature_type == FeatureType.EXON:
                parent_transcript_pk = self.__transcript_pk_ref[feature_model.id]
                parent_gene_pk = self.__transcript2gene_ref[parent_transcript_pk]
                transcript = ExonModel(
                    source_id=feature_model.id,
                    gene_id=parent_gene_pk,
                    transcript_id=parent_transcript_pk,
                    chromosome=feature_model.chromosome,
                    genomic_region=feature_model.genomic_region,
                    bin_index=bin_index,
                    external_databse_id=self.external_database_id,
                    run_id=self.run_id,
                )
                transcript.submit(session)
