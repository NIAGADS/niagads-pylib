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


BIN_INCREMENTS = [
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
        self.__chromosome_map: Dict = {}

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
        self,
        bin_root: str,
        parent_bin_range: Range,
        tree_level: int,
        sequence_length: int,
    ) -> Iterator:
        """recursive function for generating bin index"""
        max_tree_height = len(BIN_INCREMENTS)
        if tree_level >= max_tree_height:
            return

        bin_width = sequence_length if tree_level == 0 else BIN_INCREMENTS[tree_level]
        bin_range = Range(
            start=parent_bin_range.start,
            end=parent_bin_range.start + bin_width - 1,
            inclusive_end=True,
        )

        bin_number = 0
        while bin_range.start <= parent_bin_range.end:
            bin_number += 1

            bin_path = (
                xstr(bin_root) if tree_level == 0 else f"{bin_root}.B{xstr(bin_number)}"
            )

            bin_range.end = min(bin_range.end, parent_bin_range.end)

            # new range snapshot to avoid updates by reference
            yield Bin(
                genomic_region=Range(
                    start=bin_range.start,
                    end=bin_range.end,
                    inclusive_end=True,
                ),
                bin_index=bin_path,
                bin_level=tree_level,
            )

            # recursively subdivide the bin to generate child levels
            # range object is rebuilt to avoid update by reference
            child_level = tree_level + 1
            if child_level < max_tree_height:
                yield from self.__generate_chr_bins(
                    bin_root=f"{bin_path}.L{xstr(child_level)}",
                    parent_bin_range=Range(
                        start=bin_range.start,
                        end=bin_range.end,
                        inclusive_end=True,
                    ),
                    tree_level=child_level,
                    sequence_length=sequence_length,
                )

            # move to the next bin on the same level
            bin_range.start = bin_range.end + 1  # ensure bins don't overlap
            bin_range.end = bin_range.start + bin_width - 1

    def extract(self):
        for chromosome, chromosome_length in self.__chromosome_map.items():
            self.logger.info(f"Processing chromosome: {chromosome}")
            yield self.__generate_chr_bins(
                bin_root=chromosome,
                parent_bin_range=Range(
                    start=1, end=chromosome_length, inclusive_end=True
                ),
                tree_level=0,
                sequence_length=chromosome_length,
            )

    def transform(self, record: Bin):
        interval_bin = IntervalBin(**record.model_dump())
        interval_bin.run_id = self.run_id
        interval_bin.chromosome = HumanGenome(
            record.bin_index.split(".", maxsplit=1)[0]
        )
        return interval_bin

    async def load(self, session, records: list[IntervalBin]):
        IntervalBin.submit_many(session, records)
        return self.create_checkpoint(record=records[-1])
