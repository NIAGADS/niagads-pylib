from enum import auto
from niagads.enums.core import CaseInsensitiveEnum


class Strand(CaseInsensitiveEnum):
    SENSE = "+"
    ANTISENSE = "-"
