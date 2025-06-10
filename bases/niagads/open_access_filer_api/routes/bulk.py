from typing import Union

from fastapi import APIRouter, Depends, Query
from niagads.open_access_api_common.config.constants import SharedOpenAPITags
from niagads.open_access_api_common.models.records.features.bed import BEDResponse
from niagads.open_access_api_common.models.records.track.track import (
    AbridgedTrackResponse,
    TrackResponse,
)
from niagads.open_access_api_common.models.response.core import GenericResponse
from niagads.open_access_api_common.models.views.table.core import TableViewResponse
from niagads.open_access_api_common.parameters.location import span_param
from niagads.open_access_api_common.parameters.pagination import page_param
from niagads.open_access_api_common.parameters.record.query import track_list_param
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
    TRACK_DATA_STORES,
    InternalRequestParameters,
)
from niagads.open_access_filer_api.documentation import (
    APP_NAME,
    BASE_TAGS,
    OPEN_API_TAGS,
)
from niagads.open_access_filer_api.services.route import FILERRouteHelper

router = APIRouter(
    prefix="/bulk", tags=BASE_TAGS + [str(SharedOpenAPITags.TRACK_RECORD)]
)


@router.get(
    "/metadata",
    response_model=Union[
        TrackResponse, AbridgedTrackResponse, TableViewResponse, GenericResponse
    ],
    summary="get-track-metadata-bulk",
    description="Retrieve full metadata for one or more FILER track records by identifier",
)
async def get_track_metadata_bulk(
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
) -> Union[AbridgedTrackResponse, TrackResponse, TableViewResponse, GenericResponse]:

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
                    AbridgedTrackResponse
                    if rContent == ResponseContent.SUMMARY
                    else GenericResponse
                )
            ),
        ),
        Parameters(track=track),
    )
    return await helper.get_track_metadata()


tags = [
    str(SharedOpenAPITags.TRACK_DATA),
]


@router.get(
    "/data",
    tags=tags,
    summary="get-track-data-bulk",
    response_model=Union[BEDResponse, AbridgedTrackResponse, TableViewResponse],
    description="Retrieve data from one or more FILER tracks in the specified region.",
)
async def get_track_data_bulk(
    track: str = Depends(track_list_param),
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
) -> Union[BEDResponse, AbridgedTrackResponse, TableViewResponse]:

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
                    AbridgedTrackResponse
                    if rContent == ResponseContent.SUMMARY
                    else GenericResponse
                )
            ),
        ),
        Parameters(track=track, span=span, page=page),
    )

    return await helper.get_track_data()
