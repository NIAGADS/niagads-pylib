"""
Genome Reference ETL Plugins
"""

from typing import Any, Dict, Iterator, List

from niagads.common.types import ETLOperation
from niagads.database.genomicsdb.schema.reference.genome import GenomeReference
from niagads.database.genomicsdb.schema.reference.interval_bin import IntervalBin
from niagads.etl.plugins.base import AbstractBasePlugin
from niagads.etl.plugins.metadata import PluginMetadata
from niagads.etl.plugins.parameters import BasePluginParams, PathValidatorMixin
from niagads.etl.plugins.registry import PluginRegistry
from niagads.etl.plugins.types import ETLLoadStrategy
from pydantic import Field


# ============================================================================
# 1. CHROMOSOME MAP LOADER PLUGIN
# ============================================================================


class ChromosomeMapLoaderParams(BasePluginParams, PathValidatorMixin):
    """Parameters for chromosome map loader plugin."""

    file: str = Field(..., description="full path to chromosome map file")

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
        with open(self._params.file, "r") as fh:
            # TODO: implement file parsing (tab-delimited: chromosome, length)
            pass

    def transform(self, records: List[Dict[str, Any]]):
        """
        Transform chromosome map records into ORM model instances.

        Args:
            records: List of dictionaries with chromosome data

        Yields:
            GenomeReference ORM instances
        """
        for record in records:
            # TODO: implement transformation to GenomeReference ORM
            pass

    async def load(self, session, records: list[GenomeReference]): ...


# ============================================================================
# 2. INTERVAL BIN GENERATOR PLUGIN
# ============================================================================


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

    def get_record_id(self, record: IntervalBin) -> str:
        return record.bin_index

    def extract(self) -> Iterator:
        """
        Extract chromosome reference data and generate bins.

        Yields:
            Chromosome records with their lengths from the database
        """
        # TODO: implement extraction of chromosome references from database
        pass

    def transform(self, records: List[Dict[str, Any]]):
        """
        Transform chromosome data into interval bin hierarchy.

        Generates a hierarchical binning structure based on genomic coordinates.

        Args:
            records: List of chromosome records

        Yields:
            IntervalBin ORM instances
        """
        # TODO: implement bin generation algorithm
        pass

    async def load(self, session, records: list[IntervalBin]): ...


# LEGACY CODE - IGNORE FROM HERE DOWN


def read_chr_map():
    """read chr map file and store as dictionary"""
    result = OrderedDict()
    with open(args.chromosomeMap, "r") as fh:
        reader = DictReader(fh, delimiter="\t")
        for line in reader:
            chrom = line["chromosome"]
            if "chr" not in chrom:
                continue
            if chrom == "chrMT":
                chrom = "chrM"
            chrLength = int(line["length"])
            result[chrom] = chrLength

    return result


def load_bins():
    """generate and load bins"""
    for chrom, seqLength in chrMap.iteritems():
        warning("Processing", chrom)
        binRoot = chrom
        level = 0
        increments[0] = seqLength
        generate_bins(binRoot, 0, seqLength, level, seqLength)

        warning("Done with", chrom)
        if args.commit:
            database.commit()
            warning("Committed")
        else:
            database.rollback()
            warning("Rolled back")


def generate_bins(binRoot, locStart, locEnd, level, seqLength):
    """recursive function for generating bin index"""
    global binCount
    if level >= numLevels:
        return

    lowerBound = locStart
    upperBound = locStart + increments[level]

    currentBin = 0

    if locEnd > seqLength:
        locEnd = seqLength

    while lowerBound < locEnd:
        binCount = binCount + 1
        currentBin = currentBin + 1
        binLabel = binRoot + ".B" + xstr(currentBin) if level != 0 else xstr(binRoot)
        if upperBound > seqLength:
            upperBound = seqLength
        if upperBound > locEnd:
            upperBound = locEnd

        insert_bin(level, binCount, binLabel, lowerBound, upperBound)

        nextLevel = level + 1
        if nextLevel <= numLevels:
            if lowerBound == 0:
                warning("New Level:", level)

            generate_bins(
                binLabel + ".L" + xstr(nextLevel),
                lowerBound,
                upperBound,
                nextLevel,
                seqLength,
            )

        lowerBound = upperBound
        upperBound = upperBound + increments[level]


def insert_bin(level, binId, binPath, locStart, locEnd):
    """inserts bin in to db"""
    values = binPath.split(".")
    chrom = values[0]
    cursor.execute(
        insertSql, (chrom, level, binId, binPath, NumericRange(locStart, locEnd, "(]"))
    )


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Generate and load the BinIndex reference table"
    )
    parser.add_argument(
        "-m",
        "--chromosomeMap",
        help="full path file containing mapping of chr names to length; tab-delim, no header",
        required=True,
    )
    parser.add_argument(
        "--commit", action="store_true", help="run in commit mode", required=False
    )
    parser.add_argument(
        "--gusConfigFile",
        "--full path to gus config file, else assumes $GUS_HOME/config/gus.config",
    )
    args = parser.parse_args()

    increments = [
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
    binCount = 0
    numLevels = len(increments)

    chrMap = read_chr_map()
    insertSql = "INSERT INTO BinIndexRef (chromosome, level, global_bin, global_bin_path, location) VALUES (%s, %s, %s, %s, %s)"

    database = Database(args.gusConfigFile)
    database.connect()

    cursor = database.cursor()
    load_bins()

    database.close()
