from enum import auto

from niagads.enums.core import CaseInsensitiveEnum


class GenomicFeatureType(CaseInsensitiveEnum):
    GENE = auto()
    VARIANT = auto()
    STRUCTURAL_VARIANT = auto()
    REGION = auto()
