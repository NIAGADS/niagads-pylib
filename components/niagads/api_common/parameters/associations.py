import math
from typing import Union
from fastapi import HTTPException, Query
from niagads.api_common.models.annotations.associations import (
    AssociationSource,
    AssociationTrait,
)


async def association_trait_param(
    trait: AssociationTrait = Query(
        AssociationTrait.ALL,
        description="retrieve genetic associations for AD, AD-related dementias (ADRD), AD biomarkers (BIOMARKER), all AD/ADRD and AD-biomarker (ALL_AD) or all (ALL) curated associations",
    )
):
    return AssociationTrait.validate(trait, "Association Trait", AssociationTrait)


async def association_source_param(
    source: AssociationSource = Query(
        AssociationSource.ALL,
        description="retrieve genetic associations with p-value <= 1e-3 from NIAGADS-summary statistics datasets (GWAS), curated association catalogs (CURATED), or both (ALL)",
    )
):
    return AssociationSource.validate(source, "Association Source", AssociationSource)


async def pvalue_filter_param(
    pvalue: str = Query(
        default=None,
        description="retrieve p-values <= specified threshold.  Specify as decimal value or in scientific notatation (e.g., 5e-8 for genome-wide significance)",
    )
) -> float:
    if pvalue is None:
        return None
    try:
        pvalue_float = float(pvalue)
    except ValueError:
        raise HTTPException(
            status_code=422,
            detail="Invalid `pvalue` format. Must be a float (e.g., 0.00001) or scientific notation (e.g., 5e-8).",
        )
    if not (0 < pvalue_float <= 1e-3):
        raise HTTPException(
            status_code=422,
            detail="Invalid `pvalue`; p-values must be in the range (0, 1e-3]",
        )
    return pvalue_float


def neg_log10_pvalue(pvalue: float) -> Union[float, int]:
    if "e" in str(pvalue):
        mantissa, exponent = str(pvalue).split("e-")
        if abs(int(exponent)) > 300:
            return int(exponent)  # due to float size limitations

    return -1 * math.log10(pvalue)
