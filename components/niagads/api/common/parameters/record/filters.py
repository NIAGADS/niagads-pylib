from enum import auto
from typing import Optional

from fastapi import Query
from niagads.api.common.parameters.enums import EnumParameter
from niagads.api.common.utils import sanitize


async def vep_impacted_gene_param(
    gene: Optional[str] = Query(
        default=None,
        description="Ensembl identifier or official gene symbol for impacted gene",
    )
) -> str:

    return sanitize(gene)


async def vep_consequence_param(
    conseq: Optional[str] = Query(
        default=None,
        description="VEP predicted consequence; please indicated spaces with '_' (underscore) as in official sequence ontology term (see https://useast.ensembl.org/info/genome/variation/prediction/predicted_data.html)",
    )
) -> str:
    return sanitize(conseq)


async def is_adsp_variant_param(
    adsp: Optional[bool] = Query(
        default=None,
        description="filter result for variants that were identified from ADSP joint genotyping efforts and passed QC evaluations. Setting this to `false` will just return an unfiltered result, it will not filter out the ADSP variants",
    )
):
    if adsp != True:  # no falses
        return None
    else:
        return True


# TODO include INS, DEL, SNV, DUP, etc
# FIXME: use VariantClass from genomics/features/variant
class VariantType(EnumParameter):
    SNV = auto()
    SV = auto()
    ALL = auto()


async def variant_type_param(
    variantType: VariantType = Query(
        default=VariantType.ALL,
        description="variant type, for now broad category: SV or SMALL",
    )
):
    return VariantType.validate(variantType, "Variant Type", VariantType)
