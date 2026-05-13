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
from sqlalchemy_utils.types.ltree import Ltree


class GenomeReferenceLoaderParams(BasePluginParams, PathValidatorMixin):
    """Parameters for chromosome map loader plugin."""

    genome_build: Optional[GenomeBuild] = Field(
        default=GenomeBuild.GRCh38,
        description=f"Reference genome build, one of {GenomeBuild.list()}",
    )


# ============================================================================
# 1. CHROMOSOME MAP LOADER PLUGIN
# ============================================================================


class ChromosomeMapLoaderParams(GenomeReferenceLoaderParams, PathValidatorMixin):
    """Parameters for chromosome map loader plugin."""

    file: str = Field(..., description="full path to chromosome map file")

    validate_file_exists = PathValidatorMixin.validator("file")


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

    async def transform(self, record):
        """transform to genomereference object"""
        chromosome = record["chr"]
        aliases = None
        if chromosome == "chrM":
            aliases = ["chrMT"]

        chrmRef: GenomeReference = GenomeReference(
            chromosome=chromosome,
            chromosome_length=int(record["length"]),
            genome_build=str(self._params.genome_build),
            aliases=aliases,
            run_id=self.run_id,
        )
        return chrmRef

    async def load(self, session, records: list[GenomeReference]):
        await GenomeReference.submit_many(session, records)
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
    is_large_dataset=False,
    parameter_model=GenomeReferenceLoaderParams,
)


@PluginRegistry.register(metadata_bin_gen)
class IntervalBinGenerator(AbstractBasePlugin):
    """
    ETL plugin for generating and loading interval bins.

    Generates a hierarchical binning structure for genomic intervals
    from chromosome reference data and loads into the interval_bin table.
    """

    _params: GenomeReferenceLoaderParams

    def __init__(
        self,
        params: Dict[str, Any],
        name: Optional[str] = None,
        log_path: str = None,
        debug: bool = False,
        verbose: bool = False,
    ):
        super().__init__(params, name, log_path, debug, verbose)
        self.__chr_lengths: Dict = {}

    def get_record_id(self, record: IntervalBin) -> str:
        return str(record.bin_index)

    async def on_run_start(self, session):
        # get chromosome lengths from database
        async with self.session_ctx() as local_session:
            stmt = (
                select(GenomeReference.chromosome, GenomeReference.chromosome_length)
                .where(GenomeReference.genome_build == str(self._params.genome_build))
                .order_by(GenomeReference.genome_reference_id)
            )
            self.__chr_lengths = (await local_session.execute(stmt)).mappings().all()
            self.logger.debug(
                f"Retrieved {len(self.__chr_lengths)} chromosome mappings."
            )

    def __generate_chr_bins(
        self,
        bin_root: str,
        parent_bin_range: Range,
        tree_level: int,
        min_bin_width: int = 15625,
    ) -> Iterator:
        """Generate a chromosome-specific binary interval tree."""

        yield IntervalBin(
            genomic_region=Range(
                start=parent_bin_range.start,
                end=parent_bin_range.end,
                inclusive_end=True,
            ),
            bin_index=Ltree(bin_root),
            bin_level=tree_level,
            run_id=self.run_id,
            chromosome=str(HumanGenome(bin_root.split(".", maxsplit=1)[0])),
        )

        parent_bin_width = parent_bin_range.end - parent_bin_range.start + 1
        child_bin_width = parent_bin_width // 2

        if child_bin_width < min_bin_width:
            return

        left_child_end = parent_bin_range.start + child_bin_width - 1
        child_level = tree_level + 1
        child_bin_root = f"{bin_root}.L{child_level}"

        yield from self.__generate_chr_bins(
            bin_root=f"{child_bin_root}.B1",
            parent_bin_range=Range(
                start=parent_bin_range.start,
                end=left_child_end,
                inclusive_end=True,
            ),
            tree_level=tree_level + 1,
            min_bin_width=min_bin_width,
        )

        yield from self.__generate_chr_bins(
            bin_root=f"{child_bin_root}.B2",
            parent_bin_range=Range(
                start=left_child_end + 1,
                end=parent_bin_range.end,
                inclusive_end=True,
            ),
            tree_level=tree_level + 1,
            min_bin_width=min_bin_width,
        )

    def extract(self):
        for entry in self.__chr_lengths:
            chromosome = entry["chromosome"]
            chromosome_length = entry["chromosome_length"]
            self.logger.info(f"Processing chromosome: {chromosome}")
            yield from self.__generate_chr_bins(
                bin_root=chromosome,
                parent_bin_range=Range(
                    start=1, end=chromosome_length, inclusive_end=True
                ),
                tree_level=0,
            )

    async def transform(self, record: IntervalBin):
        return record

    async def load(self, session, records: list[IntervalBin]):
        await IntervalBin.submit_many(session, records)
        return self.create_checkpoint(record=records[-1])
