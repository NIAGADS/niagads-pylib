from typing import Union

from fastapi import APIRouter, Depends, Query
from niagads.exceptions.core import ValidationError
from niagads.genome.core import Assembly
from niagads.open_access_api_common.models.records.features.bed import BEDResponse
from niagads.open_access_api_common.models.records.track.track import (
    TrackResponse,
    TrackSummaryResponse,
)
from niagads.open_access_api_common.models.response.core import (
    PagedResponseModel,
)
from niagads.open_access_api_common.models.views.table.core import TableViewResponse
from niagads.open_access_api_common.parameters.location import (
    assembly_param,
    span_param,
)
from niagads.open_access_api_common.parameters.pagination import page_param
from niagads.open_access_api_common.parameters.response import (
    ResponseContent,
    ResponseFormat,
    ResponseView,
)
from niagads.open_access_api_common.parameters.text_search import keyword_param
from niagads.open_access_api_common.services.route import (
    Parameters,
    ResponseConfiguration,
)
from niagads.open_access_filer_api.dependencies import (
    TEXT_FILTER_PARAMETER,
    InternalRequestParameters,
)
from niagads.open_access_filer_api.documentation import ROUTE_NAME
from niagads.open_access_filer_api.services.route import FILERRouteHelper

router = APIRouter(prefix="/search", tags=[ROUTE_NAME, "Track Records"])

tags = [
    "Record(s) by Text Search",
]


@router.get(
    "/metadata",
    tags=tags,
    response_model=Union[
        PagedResponseModel,
        TrackSummaryResponse,
        TrackResponse,
        TableViewResponse,
    ],
    name="Search for tracks",
    description="find functional genomics tracks by a keyword search against all text fields in the track metadata",
    # description="find functional genomics tracks using category filters or by a keyword search against all text fields in the track metadata",
)
async def search_track_metadata(
    filter=Depends(TEXT_FILTER_PARAMETER),
    keyword: str = Depends(keyword_param),
    assembly: Assembly = Depends(assembly_param),
    page: int = Depends(page_param),
    content: str = Query(
        ResponseContent.FULL, description=ResponseContent.get_description(True)
    ),
    format: str = Query(
        ResponseFormat.JSON, description=ResponseFormat.generic(description=True)
    ),
    view: str = Query(
        ResponseView.DEFAULT, description=ResponseView.table(description=True)
    ),
    internal: InternalRequestParameters = Depends(),
) -> Union[PagedResponseModel, TrackSummaryResponse, TrackResponse, TableViewResponse]:

    if filter is None and keyword is None:
        raise ValidationError(
            "must specify either a `filter` and/or a `keyword` to search"
        )

    rContent = ResponseContent.validate(content, "content", ResponseContent)
    helper = FILERRouteHelper(
        internal,
        ResponseConfiguration(
            format=ResponseFormat.generic().validate(format, "format", ResponseFormat),
            content=rContent,
            view=ResponseView.table().validate(view, "view", ResponseView),
            model=(
                TrackResponse
                if rContent == ResponseContent.FULL
                else (
                    TrackSummaryResponse
                    if rContent == ResponseContent.SUMMARY
                    else PagedResponseModel
                )
            ),
        ),
        Parameters(page=page, assembly=assembly, filter=filter, keyword=keyword),
    )

    return await helper.search_track_metadata()


tags = [
    "Record(s) by Text Search",
    "Record(s) by Region",
    "Data Retrieval by Record Text Search",
    "Data Retrieval by Region",
]


@router.get(
    "/data",
    tags=tags,
    response_model=Union[
        PagedResponseModel, TrackSummaryResponse, BEDResponse, TableViewResponse
    ],
    name="Search tracks and retrieve data",
    description="find functional genomics tracks with data in specified region; qualify using category filters or by a keyword search against all text fields in the track metadata",
)
async def get_track_data_by_metadata_search(
    assembly: Assembly = Depends(assembly_param),
    span: str = Depends(span_param),
    filter=Depends(TEXT_FILTER_PARAMETER),
    keyword: str = Depends(keyword_param),
    page: int = Depends(page_param),
    content: str = Query(
        ResponseContent.FULL, description=ResponseContent.data(description=True)
    ),
    format: str = Query(
        ResponseFormat.JSON,
        description=ResponseFormat.functional_genomics(description=True),
    ),
    view: str = Query(ResponseView.DEFAULT, description=ResponseView.get_description()),
    internal: InternalRequestParameters = Depends(),
) -> Union[PagedResponseModel, TrackSummaryResponse, BEDResponse, TableViewResponse]:

    rContent = ResponseContent.data().validate(content, "content", ResponseContent)
    helper = FILERRouteHelper(
        internal,
        ResponseConfiguration(
            format=ResponseFormat.functional_genomics().validate(
                format, "format", ResponseFormat
            ),
            content=rContent,
            view=ResponseView.validate(view, "view", ResponseView),
            model=(
                BEDResponse
                if rContent == ResponseContent.FULL
                else (
                    TrackSummaryResponse
                    if rContent == ResponseContent.SUMMARY
                    else PagedResponseModel
                )
            ),
        ),
        Parameters(
            assembly=assembly, filter=filter, keyword=keyword, span=span, page=page
        ),
    )

    return await helper.search_track_data()
