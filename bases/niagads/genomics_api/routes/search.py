from typing import Union
from fastapi import APIRouter, Depends, HTTPException
from niagads.api_common.config import Settings
from niagads.api_common.constants import SharedOpenAPITags
from niagads.api_common.models.features.genomic import GenomicFeature, GenomicRegion
from niagads.api_common.models.features.variant import (
    AbridgedVariantResponse,
    VariantResponse,
)
from niagads.api_common.models.response.core import RecordResponse
from niagads.api_common.parameters.location import loc_param
from niagads.api_common.parameters.record.filters import (
    VariantType,
    variant_type_param,
    vep_impacted_gene_param,
)
from niagads.api_common.parameters.response import (
    ResponseContent,
    ResponseFormat,
    ResponseView,
)
from niagads.api_common.services.route import Parameters, ResponseConfiguration
from niagads.assembly.core import GenomicFeatureType
from niagads.genomics_api.dependencies import InternalRequestParameters
from niagads.genomics_api.documentation import APP_NAME
from niagads.genomics_api.queries.records.region import (
    RegionStructuralVariantQuery,
    RegionVariantQuery,
)
from niagads.genomics_api.services.route import GenomicsRouteHelper


router = APIRouter(
    prefix="/search",
    tags=[
        APP_NAME,
        str(SharedOpenAPITags.SEARCH),
    ],
)

MAX_SPAN = Settings.from_env().MAX_SPAN_SIZE


# TODO add params for content, format, view
@router.get(
    "/variant",
    response_model=Union[RecordResponse, VariantResponse, AbridgedVariantResponse],
    name="Search for variants [Beta]",
    description=f"Retrieve variants by region (length < {MAX_SPAN:,}) and filter for variant type or impacted gene; this endpoint is in beta, future versions will allow more extended filtering on predicted consequence and variant class",
)
async def search_varinats(
    loc: GenomicFeature = Depends(loc_param),
    variantType: VariantType = Depends(variant_type_param),
    impactedGene: str = Depends(vep_impacted_gene_param),
    internal: InternalRequestParameters = Depends(),
) -> Union[RecordResponse, VariantResponse, AbridgedVariantResponse]:

    svs_only = variantType == VariantType.SV

    # TODO update get_feature_location to return a feature
    genomic_region = await GenomicsRouteHelper(
        internal, None, None
    ).get_feature_location(loc)

    feature: GenomicFeature = GenomicFeature(
        feature_id=genomic_region, feature_type=GenomicFeatureType.REGION
    )

    genomic_region = GenomicRegion.from_region_id(feature.feature_id)

    if not feature.is_within_range_limit(MAX_SPAN) and not svs_only:
        raise HTTPException(
            status_code=404,
            detail=f"Length of query region ({feature.feature_id}) > {MAX_SPAN:,}.  Please choose a smaller window to search small variants or set `variantType=SV`",
        )

    helper = GenomicsRouteHelper(
        internal,
        ResponseConfiguration(
            content=ResponseContent.FULL,
            format=ResponseFormat.JSON,
            view=ResponseView.DEFAULT,
            model=VariantResponse,
        ),
        Parameters(
            chromosome=str(genomic_region.chromosome),
            start=genomic_region.start,
            end=genomic_region.end,
            gene=impactedGene,
        ),
        query=(RegionStructuralVariantQuery if svs_only else RegionVariantQuery),
    )

    return await helper.search_variant_records()
