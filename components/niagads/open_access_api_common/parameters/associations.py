from enum import auto
import math
from typing import Union
from fastapi import Query
from niagads.enums.core import EnumParameter


class GWASTrait(EnumParameter):
    """enum for genome builds"""

    AD = auto()
    ADRD = auto()
    BIOMARKER = auto()
    ALL_ADRD = auto()
    ALL = auto()
    OTHER = auto()


class GWASSource(EnumParameter):
    GWAS = auto()
    CURATED = auto()
    ALL = auto()


async def gwas_trait_param(
    trait: GWASTrait = Query(
        GWASTrait.ALL,
        description="retrieve genetic associations for AD, AD-related dementias (ADRD), AD biomarkers (BIOMARKER), all AD/ADRD and AD-biomarker (ALL_AD) or all (ALL) curated associations",
    )
):
    return GWASTrait.validate(trait, "GWAS Trait", GWASTrait)


async def gwas_source_param(
    source: GWASSource = Query(
        GWASSource.ALL,
        description="retrieve genetic associations with p-value <= 1e-3 from NIAGADS-summary statistics datasets (GWAS), curated association catalogs (CURATED), or both (ALL)",
    )
):
    return GWASSource.validate(source, "GWAS Source", GWASSource)


async def pvalue_filter_param(
    pvalue: float = Query(
        default=None,
        description="retrieve p-values <= specified threshold.  Specify as decimal value or in scientific notatation (e.g., 5e-8 for genome-wide significance)",
        le=1e-3,
    )
) -> float:
    return pvalue


def neg_log10_pvalue(pvalue: float) -> Union[float, int]:
    if "e" in str(pvalue):
        mantissa, exponent = str(pvalue).split("e-")
        if abs(int(exponent)) > 300:
            return int(exponent)  # due to float size limitations

    return -1 * math.log10(pvalue)
