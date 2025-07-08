from enum import auto
from fastapi import Query
from niagads.enums.core import EnumParameter


class GWASTrait(EnumParameter):
    """enum for genome builds"""

    AD = auto()
    ADRD = auto()
    BIOMARKER = auto()
    ALL_ADRD = auto()
    ALL = auto()


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
        description="retrieve genetic associations from NIAGADS-summary statistics datasets (GWAS), curated association catalogs (CURATED), or both (ALL)",
    )
):
    return GWASSource.validate(source, "GWAS Source", GWASSource)
