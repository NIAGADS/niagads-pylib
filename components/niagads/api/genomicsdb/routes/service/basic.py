from typing import List

from fastapi import APIRouter, Depends, Query
from fastapi.responses import JSONResponse
from niagads.api.common.constants import SharedOpenAPITags
from niagads.api.common.models.records import Entity
from niagads.api.common.models.search.records import RecordSearchResult
from niagads.api.common.models.response.core import (
    RecordResponse,
)
from niagads.api.common.parameters.pagination import limit_param
from niagads.api.common.parameters.response import (
    ResponseContent,
    ResponseFormat,
    ResponseView,
)
from niagads.api.common.services.route import (
    Parameters,
    ResponseConfiguration,
)
from niagads.api.genomicsdb.dependencies import InternalRequestParameters
from niagads.api.genomicsdb.documentation import BASE_TAGS
from niagads.api.genomicsdb.queries.services.search import (
    SearchType,
    SiteSearchQuery,
)
from niagads.api.genomicsdb.services.route import (
    GenomicsRouteHelper,
    QueryOptions,
)
from niagads.utils.regular_expressions import RegularExpressions
from niagads.utils.string import matches


router = APIRouter(prefix="/service", tags=BASE_TAGS + [str(SharedOpenAPITags.SERVICE)])


@router.get(
    "/search",
    response_model=List[RecordSearchResult],
    summary="search-feature-and-track-records",
    description="Find Alzheimer's GenomicsDB Records (features, tracks, collections) by identifier or keyword",
)
async def site_search(
    keyword: str = Query(
        description="feature identifier or keyword (NOTE: searches for gene symbols use exact, case-sensitive, matching)"
    ),
    searchType: SearchType = Query(
        default=SearchType.GLOBAL, description=SearchType.get_description()
    ),
    content: str = Query(
        ResponseContent.FULL,
        description=ResponseContent.data(description=True),
    ),
    limit: int = Depends(limit_param),
    internal: InternalRequestParameters = Depends(),
) -> List[RecordSearchResult]:

    # postgres throws a conversion error if it ends w/a symbol,
    # so drop the symbol and match everything up to it
    if keyword.endswith(":") or keyword.endswith("-"):
        keyword = keyword[:-1]

    response_content = ResponseContent.data().validate(
        content, "content", ResponseContent
    )

    query = SiteSearchQuery(search_type=searchType)
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

    # test to see if genomic location
    if searchType == SearchType.GLOBAL or SearchType.FEATURE:

        if matches(RegularExpressions.GENOMIC_LOCATION, keyword):
            if response_content == ResponseContent.COUNTS:
                return JSONResponse({"result_size": 1})
            return [
                RecordSearchResult(
                    primary_key=keyword,
                    description="",
                    display=keyword,
                    record_type=Entity.REGION,
                    match_rank=-1,
                    matched_term=keyword,
                )
            ]

    result = await helper.get_query_response(opts=QueryOptions(raw_response=True))
    result_size = len(result)
    if limit:
        result = result[:limit]

    if response_content == ResponseContent.COUNTS:
        if limit:
            return JSONResponse(
                {"limited_result_size": len(result), "result_size": result_size}
            )
        return JSONResponse({"result_size": result_size})

    return result
