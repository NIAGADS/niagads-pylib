from typing import List, Union
from fastapi import APIRouter, Depends, Query
from fastapi.responses import JSONResponse
from niagads.api_common.constants import SharedOpenAPITags
from niagads.api_common.models.features.genomic import GenomicRegion
from niagads.api_common.models.search.records import RecordSearchResult
from niagads.api_common.models.response.core import (
    RecordResponse,
    T_RecordResponse,
)
from niagads.api_common.parameters.response import (
    ResponseContent,
    ResponseFormat,
    ResponseView,
)
from niagads.api_common.services.route import (
    Parameters,
    ResponseConfiguration,
)
from niagads.genomics_api.dependencies import InternalRequestParameters
from niagads.genomics_api.documentation import BASE_TAGS
from niagads.genomics_api.queries.igvbrowser import IGVFeatureLookupQuery
from niagads.genomics_api.queries.search import (
    SearchType,
    SiteSearchQuery,
)
from niagads.genomics_api.services.route import (
    GenomicsRouteHelper,
    QueryOptions,
)


router = APIRouter(prefix="/service", tags=BASE_TAGS)

tags = [str(SharedOpenAPITags.RECORD_SEARCH), str(SharedOpenAPITags.LOOKUP_SERVICES)]


@router.get(
    "/search",
    response_model=Union[List[RecordSearchResult]],
    tags=tags,
    summary="search-feature-and-track-records",
    description="Find Alzheimer's GenomicsDB Records (features, tracks, collections) by identifier or keyword",
)
async def site_search(
    keyword: str = Query(
        description="feature identifier or keyword (NOTE: searches for gene symbols use exact, case-sensitive, matching)"
    ),
    search_type: SearchType = Query(
        default=SearchType.GLOBAL, description=SearchType.get_description()
    ),
    internal: InternalRequestParameters = Depends(),
) -> Union[List[RecordSearchResult]]:

    query = SiteSearchQuery(searchType=search_type)

    helper = GenomicsRouteHelper(
        internal,
        ResponseConfiguration(
            format=ResponseFormat.JSON,
            content=ResponseContent.FULL,
            view=ResponseView.DEFAULT,
            model=RecordResponse,
        ),
        Parameters(keyword=keyword),
        query=query,
    )

    return await helper.get_query_response(opts=QueryOptions(raw_response=True))


tags = [str(SharedOpenAPITags.GENOME_BROWSER)]


@router.get(
    "/igvbrowser/feature",
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

    result: T_RecordResponse = await helper.get_query_response()

    if len(result.data) == 0:
        return JSONResponse({})  # result.response

    # add the flank
    region = GenomicRegion(**result.data)
    region.start -= flank
    region.end += flank

    return region
