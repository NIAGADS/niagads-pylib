from fastapi import Depends, Query, APIRouter
from fastapi.responses import JSONResponse
from niagads.api_common.constants import SharedOpenAPITags
from niagads.api_common.models.features.genomic import GenomicRegion
from niagads.api_common.models.response.core import RecordResponse, T_RecordResponse
from niagads.api_common.parameters.response import (
    ResponseContent,
    ResponseFormat,
    ResponseView,
)
from niagads.api_common.services.route import Parameters, ResponseConfiguration
from niagads.genomics_api.dependencies import InternalRequestParameters
from niagads.genomics_api.documentation import BASE_TAGS
from niagads.genomics_api.queries.igvbrowser.service import IGVFeatureLookupQuery
from niagads.genomics_api.services.route import GenomicsRouteHelper, QueryOptions


router = APIRouter(prefix="/service/igvbrowser", tags=BASE_TAGS)


tags = [str(SharedOpenAPITags.GENOME_BROWSER), str(SharedOpenAPITags.LOOKUP_SERVICES)]


@router.get(
    "/feature",
    tags=tags + [str(SharedOpenAPITags.LOOKUP_SERVICES)],
    response_model=GenomicRegion,
    response_model_exclude_none=True,
    summary="genome-browser-feature-lookup",
    description="retrieve genomic location (variants) or footprint (genes) feature in the format required by the NIAGADS Genome Browser",
)
async def get_browser_feature_region(
    id: str,
    flank: int = Query(
        default=0,
        description="add flanking region +/- `flank` kb up- and downstream to the returned feature location",
    ),
    internal: InternalRequestParameters = Depends(),
) -> GenomicRegion:

    helper = GenomicsRouteHelper(
        internal,
        ResponseConfiguration(
            format=ResponseFormat.JSON,
            content=ResponseContent.FULL,
            view=ResponseView.DEFAULT,
            model=RecordResponse,
        ),
        Parameters(id=id),
        query=IGVFeatureLookupQuery,
    )

    result: dict = await helper.get_query_response(opts=QueryOptions(raw_response=True))

    if len(result) == 0:
        return JSONResponse({})  # result.response

    # add the flank
    region = GenomicRegion(**result[0])
    region.start -= flank
    region.end += flank

    return region
