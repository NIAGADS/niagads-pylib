"""
Genome Reference ETL Plugins
"""

from typing import Any, Dict, Iterator, List, Optional

from niagads.common.models.types import Range
from niagads.common.types import ETLOperation
from niagads.csv_parser.core import CSVFileParser
from niagads.database.genomicsdb.schema.reference.genome import GenomeReference
from niagads.database.genomicsdb.schema.reference.interval_bin import IntervalBin
from niagads.etl.plugins.base import AbstractBasePlugin
from niagads.etl.plugins.metadata import PluginMetadata
from niagads.etl.plugins.parameters import BasePluginParams, PathValidatorMixin
from niagads.etl.plugins.registry import PluginRegistry
from niagads.etl.plugins.types import ETLLoadStrategy
from niagads.utils.string import xstr
from pydantic import BaseModel, Field

from niagads.genome_reference.human import GenomeBuild, HumanGenome
from sqlalchemy import select


# ============================================================================
# 1. CHROMOSOME MAP LOADER PLUGIN
# ============================================================================


class ChromosomeMapLoaderParams(BasePluginParams, PathValidatorMixin):
    """Parameters for chromosome map loader plugin."""

    file: str = Field(..., description="full path to chromosome map file")
    genome_build: GenomeBuild = Field(
        default=GenomeBuild.GRCh38,
        description=f"Reference genome build, one of {GenomeBuild.list()}",
    )

    validate_file_exists = PathValidatorMixin.validator("file", is_dir=False)


metadata_chr_map = PluginMetadata(
    version="1.0",
    description="ETL Plugin to load chromosome map reference data",
    affected_tables=[GenomeReference],
    load_strategy=ETLLoadStrategy.CHUNKED,
    operation=ETLOperation.INSERT,
    is_large_dataset=False,
    parameter_model=ChromosomeMapLoaderParams,
)


@PluginRegistry.register(metadata_chr_map)
class ChromosomeMapLoader(AbstractBasePlugin):
    """
    ETL plugin for loading chromosome map reference data.

    Loads chromosome names and lengths from a tab-delimited file.
    """

    _params: ChromosomeMapLoaderParams

    def get_record_id(self, record: GenomeReference) -> str:
        return record.chromosome

    def extract(self) -> Iterator:
        """
        Extract chromosome map from file.

        Yields:
            Dictionary with chromosome name and length
        """
        parser = CSVFileParser(file=self._params.file, header=False)
        parser.header_fields(["chr", "length"])
        for row in parser:
            if row["chr"] == "chrMT":
                row["chr"] == "chrM"
            try:
                HumanGenome(row["chr"])  # primary assembly only
                yield row
            except:
                pass

    def transform(self, record):
        """transform to genomereference object"""
        chromosome = record["chr"]
        aliases = None
        if chromosome == "chrM":
            aliases = ["chrMT"]

        chrmRef: GenomeReference = GenomeReference(
            chromosome=chromosome,
            chromosome_length=record["length"],
            aliases=aliases,
            run_id=self.run_id,
        )
        return chrmRef

    async def load(self, session, records: list[GenomeReference]):
        GenomeReference.submit(session, records)
        return self.create_checkpoint(record=records[-1])


# ============================================================================
# 2. INTERVAL BIN GENERATOR PLUGIN
# ============================================================================


class Bin(BaseModel):
    genomic_region: Range
    bin_index: str
    bin_level: int


metadata_bin_gen = PluginMetadata(
    version="1.0",
    description="ETL Plugin to generate and load interval bin reference data",
    affected_tables=[IntervalBin],
    load_strategy=ETLLoadStrategy.CHUNKED,
    operation=ETLOperation.INSERT,
    is_large_dataset=True,
    parameter_model=BasePluginParams,
)


@PluginRegistry.register(metadata_bin_gen)
class IntervalBinGenerator(AbstractBasePlugin):
    """
    ETL plugin for generating and loading interval bins.

    Generates a hierarchical binning structure for genomic intervals
    from chromosome reference data and loads into the interval_bin table.
    """

    def __init__(
        self,
        params: Dict[str, Any],
        name: Optional[str] = None,
        log_path: str = None,
        debug: bool = False,
        verbose: bool = False,
    ):
        super().__init__(params, name, log_path, debug, verbose)
        self.__bin_count = 0
        self.__chromosome_map: Dict = {}
        self.__bins = []
        self.__bin_increments = [
            -1,
            64000000,
            32000000,
            16000000,
            8000000,
            4000000,
            2000000,
            1000000,
            500000,
            250000,
            125000,
            62500,
            31250,
            15625,
        ]

    def get_record_id(self, record: IntervalBin) -> str:
        return record.bin_index

    async def on_run_start(self, session):
        # get chromosome lengths from database
        async with self.session_ctx() as local_session:
            stmt = select(
                GenomeReference.chromosome, GenomeReference.chromosome_length
            ).order_by(GenomeReference.genome_reference_id)
            result = await local_session.execute(stmt).mappings()
            self.__chromosome_map = result.all()

    def __generate_chr_bins(
        self, bin_root: str, range: Range, level: int, sequence_length: int
    ):
        """recursive function for generating bin index"""
        num_levels = len(self.__bin_increments)
        if level >= num_levels:
            return

        bin_lower_bound = range.start
        bin_upper_bound = range.start + self.__bin_increments[level]

        if range.end > sequence_length:
            range.end = sequence_length

        while bin_lower_bound <= range.end:
            self.__bin_count += 1
            if bin_upper_bound > range.end:
                bin_upper_bound = range.end

            bin_path = (
                xstr(bin_root)
                if level == 0
                else bin_root + ".B" + xstr(self.__bin_count)
            )

            self.__bins.append(
                Bin(
                    genomic_region=Range(start=bin_lower_bound, end=bin_upper_bound),
                    bin_index=bin_path,
                    bin_level=level,
                )
            )

            next_level = level + 1
            if next_level <= num_levels:
                self.__generate_chr_bins(
                    bin_root=bin_path + ".L" + xstr(next_level),
                    range=Range(start=bin_lower_bound, end=bin_upper_bound),
                    level=next_level,
                    sequence_length=sequence_length,
                )

            bin_lower_bound = bin_upper_bound + 1  # ensure bins don't overlap
            bin_upper_bound = bin_upper_bound + self.__bin_increments[level]

    def extract(self):
        for chromosome, chromosome_length in self.__chromosome_map.items():
            self.logger.info(f"Processing chromosome: {chromosome}")
            self.__bin_increments[0] = chromosome_length
            self.__bins = []  # clear bins
            bins = self.__generate_chr_bins(
                bin_root=chromosome,
                range=Range(start=1, end=chromosome_length),
                level=0,
                sequence_length=chromosome_length,
            )

    def transform(self, record):

        # TODO: implement bin generation algorithm
        pass

    async def load(self, session, records: list[IntervalBin]): ...


# LEGACY CODE - IGNORE FROM HERE DOWN


def insert_bin(level, binId, binPath, locStart, locEnd):
    """inserts bin in to db"""
    values = binPath.split(".")
    chrom = values[0]
    cursor.execute(
        insertSql, (chrom, level, binId, binPath, NumericRange(locStart, locEnd, "(]"))
    )

    chrMap = read_chr_map()
    insertSql = "INSERT INTO BinIndexRef (chromosome, level, global_bin, global_bin_path, location) VALUES (%s, %s, %s, %s, %s)"

    database = Database(args.gusConfigFile)
    database.connect()

    cursor = database.cursor()
    load_bins()

    database.close()
