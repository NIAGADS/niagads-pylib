from fastapi import Depends, Query, APIRouter
from fastapi.responses import JSONResponse
from niagads.api.common.constants import SharedOpenAPITags
from niagads.api.common.models.features.genomic import GenomicRegion
from niagads.api.common.models.response.core import RecordResponse, T_RecordResponse
from niagads.api.common.parameters.response import (
    ResponseContent,
    ResponseFormat,
    ResponseView,
)
from niagads.api.common.services.route import Parameters, ResponseConfiguration
from niagads.api.genomicsdb.dependencies import InternalRequestParameters
from niagads.api.genomicsdb.documentation import BASE_TAGS
from niagads.api.genomicsdb.queries.igvbrowser.service import IGVFeatureLookupQuery
from niagads.api.genomicsdb.services.route import GenomicsRouteHelper, QueryOptions


router = APIRouter(
    prefix="/service/igvbrowser", tags=BASE_TAGS + [str(SharedOpenAPITags.SERVICE)]
)


@router.get(
    "/feature",
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
