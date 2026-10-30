from enum import auto
from typing import Annotated, Optional

from fastapi import Query
from niagads.api.common.parameters.validators import sanitize_enum_value
from niagads.api.common.types import VariantClassFilter
from niagads.api.common.utils import sanitize
from niagads.enums.core import CaseInsensitiveEnum
from pydantic import BeforeValidator


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
        description="VEP predicted consequence (see https://useast.ensembl.org/info/genome/variation/prediction/predicted_data.html)",
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


async def variant_type_parameter(
    variant_type: Annotated[
        VariantClassFilter,
        BeforeValidator(sanitize_enum_value(VariantClassFilter)),
        Query(
            description=(
                f"Type of variants to query: "
                "structural variants (SNV) vs short variants (SHORT) "
                "such as SNVs and short INDELs or all matches (ALL). "
                "If ranged query and range >50kb, only SVs will be returned."
            )
        ),
    ] = VariantClassFilter.ALL,
) -> VariantClassFilter:
    return variant_type
