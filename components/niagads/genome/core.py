import csv
import logging
from enum import auto

from niagads.enums.core import CaseInsensitiveEnum
from niagads.utils.string import xstr


class Human(CaseInsensitiveEnum):
    # name, value pair
    # e.g., for chr in Chromosome: print(chr.name)
    # will print a new line sep list of chr1 chr2 chr3, etc
    # print(chr.value) will print 1 2 3, etc.
    chr1 = "1"
    chr2 = "2"
    chr3 = "3"
    chr4 = "4"
    chr5 = "5"
    chr6 = "6"
    chr7 = "7"
    chr8 = "8"
    chr9 = "9"
    chr10 = "10"
    chr11 = "11"
    chr12 = "12"
    chr13 = "13"
    chr14 = "14"
    chr15 = "15"
    chr16 = "16"
    chr17 = "17"
    chr18 = "18"
    chr19 = "19"
    chr20 = "20"
    chr21 = "21"
    chr22 = "22"
    chrX = "X"
    chrY = "Y"
    chrM = "M"

    # after from https://stackoverflow.com/a/76131490
    @classmethod
    def _missing_(cls, value: str):  # allow 'X' or 'chrX'
        for member in cls:
            if value == member.name:
                return member
        return super()._missing_(cls, value)

    def __str__(self):
        return self.name

    @classmethod
    def list(cls):
        """return a list of the enum values"""
        return [f"chr{v}" for v in super().list()]

    @classmethod
    def sort_order(self):
        """returns a {chr:order} mapping to faciliate chr based sorting"""
        return {chr: index for index, chr in enumerate(self.__members__)}

    @classmethod
    def validate(self, value: str, inclPrefix: bool = True):
        """
        validate a chromosome value against the enum; if match found will return match

        Args:
            value (str): value to match
            inclPrefix (bool, optional): include 'chr' prefix in the return. Defaults to True.
        """
        # make sure X,Y,M are uppercase; MT -> M
        cv = str(value).upper().replace("CHR", "").replace("MT", "M")
        if cv in self._value2member_map_:
            return "chr" + cv if inclPrefix else cv
        else:
            raise KeyError(f"Invalid chromosome: {value}")


class ChromosomeMapParser(object):
    """Generator for chromosome map parser/object
    parses mappings of third party chromosome sequence ids (e.g., refseq) to chromosome number
    may also include chromosome length
    - for now assumes the tab-delim with at least the following columns:
    > source_id       chromosome     length
    """

    def __init__(self, fileName: str, verbose: bool = False, debug: bool = False):
        """ChromosomeMap base class initializer.
        Args:
            fileName (_type_): full path to chromosome mapping file
            verbose (bool, optional): verbose output flag. Defaults to False.
            debug (bool, optional): debug flag. Defaults to False.

        Returns:
            An instance of a ChromosomeMap with initialized mapping dict
        """
        self._verbose = verbose
        self._debug = debug
        self.logger = logging.getLogger(__name__)

        self.__file = fileName
        self.__map = {}
        self.__parse_mapping()

    def __parse_mapping(self):
        """parse chromosome map"""

        if self._verbose:
            self.logger.info("Loading chromosome map from:", self.__file)

        with open(self.__file, "r") as fh:
            reader = csv.DictReader(fh, delimiter="\t")
            for row in reader:
                # source_id	chromosome	chromosome_order_num	length
                key = row["source_id"]
                value = row["chromosome"].replace("chr", "")
                self.__map[key] = value

    def chromosome_map(self):
        "Get the chromosome map."
        return self.__map

    def get_sequence_id(self, chrmNum):
        """Given a chromosome number, tries to find matching sequence id."""
        for sequenceId, cn in self.__map.items():
            if cn == chrmNum or cn == "chr" + xstr(chrmNum):
                return sequenceId

        return None

    def get(self, sequenceId):
        """Return chromosome number mapped to the provided sequence ID."""
        # want to raise AttributeError if not in the map, so not checking
        return self.__map[sequenceId]


class Strand(CaseInsensitiveEnum):
    SENSE = "+"
    ANTISENSE = "-"


class Assembly(CaseInsensitiveEnum):
    """enum for genome builds"""

    GRCh37 = "GRCh37"
    GRCh38 = "GRCh38"

    @classmethod
    def _missing_(cls, value: str):
        """Override super to map hg19 or hg38 to GRCh* nomenclature.
        For everything else call super() to allow case-insensitive matches"""
        if value.lower() == "hg19":
            return cls.GRCh37
        if value.lower() == "hg38":
            return cls.GRCh38
        return super(Assembly, cls)._missing_(value)

    @classmethod
    def list(cls):
        """return a list of the enum values"""
        return super(Assembly, cls).list() + ["hg19", "hg38"]

    def hg_label(self):
        return "hg19" if self.value == "GRCh37" else "hg38"

    # these class methods are from EnumParameters
    # no inheritence here b/c of functional programming
    # and limitations on subclassing Enums
    @classmethod
    def get_description(cls):
        return f"Allowable values are: {','.join(cls.list())}."

    @classmethod
    def validate(cls, value, label: str, returnCls: CaseInsensitiveEnum):
        from niagads.exceptions.core import ValidationError
        from niagads.utils.string import sanitize  # avoid circular import

        try:
            cls(sanitize(value))
            return returnCls(value)
        except Exception as err:
            raise ValidationError(
                f"Invalid value provided for `{label}`: {value}.  {cls.get_description()}"
            )


class GenomicFeatureType(CaseInsensitiveEnum):
    GENE = auto()
    VARIANT = auto()
    STRUCTURAL_VARIANT = auto()
    REGION = auto()
