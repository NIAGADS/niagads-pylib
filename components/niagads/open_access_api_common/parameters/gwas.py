from enum import auto
from fastapi import Query
from niagads.enums.core import EnumParameter


class GWASTrait(EnumParameter):
    """enum for genome builds"""

    AD = auto()
    ADRD = auto()
    AD_ADRD = auto()
    ALL = auto()


class GWASSource(EnumParameter):
    NIAGADS = auto()
    CATALOG = auto()
    ALL = auto()


async def gwas_trait_param(
    trait: GWASTrait = Query(
        GWASTrait.ALL,
        description="retrieve genetic associations for AD, AD-related dementias (ADRD), AD/ADRD or all curated associations",
    )
):
    return GWASTrait.validate(trait, "GWAS Trait", GWASTrait)


async def gwas_source_param(
    trait: GWASSource = Query(
        GWASSource.ALL,
        description="retrieve genetic associations from NIAGADS-summary statistics datasets, curated assocation catalogs, or both",
    )
):
    return GWASSource.validate(trait, "GWAS Source", GWASTrait)
