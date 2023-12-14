from .excel import ExcelFileParser
from .csv import CSVFileParser

from .adsp_consequence import ConsequenceParser
from .vcf import VCFEntryParser
from .vep_json import VEPJSONParser, CONSEQUENCE_TYPES, CODING_CONSEQUENCES, is_coding_consequence
from .chromosome_map import ChromosomeMapParser