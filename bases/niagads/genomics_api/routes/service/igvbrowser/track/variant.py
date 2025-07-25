from typing import Optional
from fastapi import Depends, Query, APIRouter
from fastapi.responses import JSONResponse
from niagads.api_common.constants import SharedOpenAPITags
from niagads.api_common.models.features.genomic import GenomicFeature, GenomicRegion
from niagads.api_common.models.response.core import RecordResponse
from niagads.api_common.parameters.igvbrowser import ADSPRelease, AnnotatedVariantTrack
from niagads.api_common.parameters.location import loc_param
from niagads.api_common.parameters.record.query import (
    adsp_release_param,
    variant_track_param,
)
from niagads.api_common.parameters.response import (
    ResponseContent,
    ResponseFormat,
    ResponseView,
)
from niagads.api_common.services.route import Parameters, ResponseConfiguration
from niagads.genomics_api.dependencies import InternalRequestParameters
from niagads.genomics_api.documentation import BASE_TAGS
from niagads.genomics_api.queries.igvbrowser.service import IGVFeatureLookupQuery

from niagads.genomics_api.queries.igvbrowser.tracks.variant import select_track_query
from niagads.genomics_api.services.route import GenomicsRouteHelper, QueryOptions


router = APIRouter(
    prefix="/service/igvbrowser/track",
    tags=BASE_TAGS + [str(SharedOpenAPITags.SERVICE)],
)


@router.get(
    "/variant",
    response_model_exclude_none=True,
    summary="genome-browser-feature-lookup",
    description="retrieve genomic location (variants) or footprint (genes) feature in the format required by the NIAGADS Genome Browser",
)
async def get_variant_browser_track_data(
    track: str = Depends(variant_track_param),
    release: Optional[str] = Depends(adsp_release_param),
    span: GenomicFeature = Depends(loc_param),
    internal: InternalRequestParameters = Depends(),
):

    genomic_region = GenomicRegion.from_region_id(span.feature_id)

    selected_release = (
        "R4"
        if "ADSP" in str(track) and release is None
        else str(release) if release is not None else None
    )

    helper = GenomicsRouteHelper(
        internal,
        ResponseConfiguration(
            format=ResponseFormat.JSON,
            content=ResponseContent.FULL,
            view=ResponseView.DEFAULT,
            model=RecordResponse,
        ),
        Parameters(
            id=id,
            adsp_release=selected_release,
            svs_only=track == AnnotatedVariantTrack.ADSP_SV,
            chromosome=str(genomic_region.chromosome),
            start=genomic_region.start,
            end=genomic_region.end,
        ),
        query=select_track_query(track),
    )

    response = await helper.get_query_response(opts=QueryOptions(raw_response=True))
    return response[0]["result"]
