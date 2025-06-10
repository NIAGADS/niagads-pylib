from typing import List, Union
from fastapi import APIRouter, Depends, Query
from fastapi.responses import JSONResponse
from niagads.open_access_api_common.config.constants import SharedOpenAPITags
from niagads.open_access_api_common.models.records.features.genomic import GenomicRegion
from niagads.open_access_api_common.models.records.search import RecordSearchResult
from niagads.open_access_api_common.models.response.core import (
    GenericResponse,
    T_GenericResponse,
)
from niagads.open_access_api_common.parameters.response import (
    ResponseContent,
    ResponseFormat,
    ResponseView,
)
from niagads.open_access_api_common.services.route import (
    Parameters,
    ResponseConfiguration,
)
from niagads.open_access_genomics_api.dependencies import InternalRequestParameters
from niagads.open_access_genomics_api.documentation import APP_NAME
from niagads.open_access_genomics_api.queries.igvbrowser import IGVFeatureLookupQuery
from niagads.open_access_genomics_api.queries.search import (
    SearchType,
    SiteSearchQueryDefinition,
)
from niagads.open_access_genomics_api.services.route import GenomicsRouteHelper


router = APIRouter(prefix="/service", tags=[APP_NAME])

tags = [str(SharedOpenAPITags.LOOKUP_SERVICES)]


@router.get(
    "/search",
    response_model=Union[List[RecordSearchResult]],
    name="Database Search",
    description="Find Alzheimer's GenomicsDB Records (features, tracks, collections) by identifier or keyword",
)
async def site_search(
    keyword: str = Query(
        description="feature identifier or keyword (NOTE: searches for gene symbols use exact, case-sensitive, matching)"
    ),
    searchType: SearchType = Query(
        default=SearchType.GLOBAL, description=SearchType.get_description()
    ),
    internal: InternalRequestParameters = Depends(),
) -> Union[List[RecordSearchResult]]:

    query = SiteSearchQueryDefinition(searchType=searchType)

    test = {
        "primary_key": "ENSG00000130203",
        "display": "APOE",
        "record_type": "gene",
        "match_rank": 0,
        "matched_term": "APOE",
        "description": "Gene // protein coding // apolipoprotein E // Also Known As: AD2 // Location: 19q13.32",
    }

    x = RecordSearchResult(**test)

    helper = GenomicsRouteHelper(
        internal,
        ResponseConfiguration(
            format=ResponseFormat.JSON,
            content=ResponseContent.FULL,
            view=ResponseView.DEFAULT,
            model=GenericResponse,
        ),
        Parameters(keyword=keyword),
        query=query,
    )

    result: T_GenericResponse = await helper.get_query_response()
    if len(result.data) == 0:
        return JSONResponse([])

    return result.data


tags = [str(SharedOpenAPITags.GENOME_BROWSER)]


@router.get(
    "/igvbrowser/feature",
    tags=tags,
    response_model=GenomicRegion,
    response_model_exclude_none=True,
    name="IGV Genome Browser feature lookup service",
    description="retrieve genomic location (variants) or footprint (genes) feature in the format required by the IGV Browser",
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
            model=GenericResponse,
        ),
        Parameters(id=id),
        query=IGVFeatureLookupQuery,
    )

    result: T_GenericResponse = await helper.get_query_response()

    if len(result.data) == 0:
        return JSONResponse({})  # result.response

    # add the flank
    region = GenomicRegion(**result.data)
    region.start -= flank
    region.end += flank

    return region
