from typing import Union

from fastapi import APIRouter, Depends, Query
from niagads.exceptions.core import ValidationError
from niagads.genome.core import Assembly
from niagads.open_access_api_common.models.records.track.track import (
    TrackResponse,
    TrackSummaryResponse,
)
from niagads.open_access_api_common.models.response.core import (
    PagedResponseModel,
    ResponseModel,
)
from niagads.open_access_api_common.models.views.table.core import TableViewResponse
from niagads.open_access_api_common.parameters.location import assembly_param
from niagads.open_access_api_common.parameters.pagination import page_param
from niagads.open_access_api_common.parameters.record.query import track_list_param
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
from niagads.open_access_filer_api.services.route import FILERRouteHelper

router = APIRouter(prefix="/metadata")

tags = ["Track Metadata by ID"]


@router.get(
    "/",
    tags=tags,
    response_model=Union[
        TrackResponse, TrackSummaryResponse, TableViewResponse, ResponseModel
    ],
    name="Get metadata for multiple tracks",
    description="retrieve full metadata for one or more FILER track records",
)
async def get_track_metadata(
    track: str = Depends(track_list_param),
    content: str = Query(
        ResponseContent.FULL,
        description=ResponseContent.descriptive(inclUrls=True, description=True),
    ),
    format: str = Query(
        ResponseFormat.JSON, description=ResponseFormat.generic(description=True)
    ),
    view: str = Query(
        ResponseView.DEFAULT, description=ResponseView.table(description=True)
    ),
    internal: InternalRequestParameters = Depends(),
) -> Union[TrackSummaryResponse, TrackResponse, TableViewResponse, ResponseModel]:

    rContent = ResponseContent.descriptive(inclUrls=True).validate(
        content, "content", ResponseContent
    )
    helper = FILERRouteHelper(
        internal,
        ResponseConfiguration(
            format=ResponseFormat.generic().validate(format, "format", ResponseFormat),
            view=ResponseView.table().validate(view, "view", ResponseView),
            content=rContent,
            model=(
                TrackResponse
                if rContent == ResponseContent.FULL
                else (
                    TrackSummaryResponse
                    if rContent == ResponseContent.SUMMARY
                    else ResponseModel
                )
            ),
        ),
        Parameters(track=track),
    )
    return await helper.get_track_metadata()


tags = ["Record(s) by Text Search"] + ["Track Metadata by Text Search"]


@router.get(
    "/search",
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
