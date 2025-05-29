from typing import Union

from fastapi import APIRouter, Depends, Query
from niagads.open_access_api_common.config.constants import SharedOpenAPITags
from niagads.open_access_api_common.models.records.features.bed import BEDResponse
from niagads.open_access_api_common.models.records.track.track import (
    TrackResponse,
    TrackSummaryResponse,
)
from niagads.open_access_api_common.models.response.core import (
    PagedResponseModel,
    ResponseModel,
)
from niagads.open_access_api_common.models.views.table.core import TableViewResponse
from niagads.open_access_api_common.parameters.location import (
    assembly_param,
    span_param,
)
from niagads.open_access_api_common.parameters.pagination import page_param
from niagads.open_access_api_common.parameters.record.path import track_param
from niagads.open_access_api_common.parameters.response import (
    ResponseContent,
    ResponseFormat,
    ResponseView,
)
from niagads.open_access_api_common.services.route import (
    Parameters,
    ResponseConfiguration,
)
from niagads.open_access_filer_api.dependencies import (
    InternalRequestParameters,
)
from niagads.open_access_filer_api.documentation import ROUTE_NAME
from niagads.open_access_filer_api.services.route import FILERRouteHelper

router = APIRouter(
    prefix="/track",
    tags=[
        ROUTE_NAME,
        str(SharedOpenAPITags.TRACK_RECORD),
    ],
)


@router.get(
    "/{track}",
    tags=[str(SharedOpenAPITags.RECORD_BY_ID)],
    response_model=Union[TrackSummaryResponse, TrackResponse, ResponseModel],
    name="Get track metadata",
    description="retrieve track metadata for the FILER record identified by the `track` specified in the path; use `content=summary` for a brief response",
)
async def get_track_metadata(
    track=Depends(track_param),
    content: str = Query(
        ResponseContent.SUMMARY,
        description=ResponseContent.descriptive(description=True),
    ),
    format: str = Query(
        ResponseFormat.JSON, description=ResponseFormat.generic(description=True)
    ),
    internal: InternalRequestParameters = Depends(),
) -> Union[TrackSummaryResponse, TrackResponse, ResponseModel]:

    rContent = ResponseContent.descriptive().validate(
        content, "content", ResponseContent
    )
    rFormat = ResponseFormat.generic().validate(format, "format", ResponseFormat)
    helper = FILERRouteHelper(
        internal,
        ResponseConfiguration(
            content=rContent,
            format=rFormat,
            model=(
                TrackResponse
                if rContent == ResponseContent.FULL
                else TrackSummaryResponse
            ),
        ),
        Parameters(track=track),
    )

    return await helper.get_track_metadata()


tags = [
    str(SharedOpenAPITags.RECORD_BY_ID),
    str(SharedOpenAPITags.RECORD_BY_REGION),
    str(SharedOpenAPITags.TRACK_DATA),
]


@router.get(
    "/{track}/data",
    tags=tags,
    name="Get track data",
    response_model=Union[
        BEDResponse, TrackSummaryResponse, TableViewResponse, PagedResponseModel
    ],
    description="retrieve functional genomics track data from FILER in the specified region; specify `content=counts` to just retrieve a count of the number of hits in the specified region",
)
async def get_track_data(
    track=Depends(track_param),
    span: str = Depends(span_param),
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
) -> Union[BEDResponse, TrackSummaryResponse, TableViewResponse, PagedResponseModel]:

    rContent = ResponseContent.data().validate(content, "content", ResponseContent)
    helper = FILERRouteHelper(
        internal,
        ResponseConfiguration(
            content=rContent,
            format=ResponseFormat.functional_genomics().validate(
                format, "format", ResponseFormat
            ),
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
        Parameters(track=track, span=span, page=page),
    )

    return await helper.get_track_data()
