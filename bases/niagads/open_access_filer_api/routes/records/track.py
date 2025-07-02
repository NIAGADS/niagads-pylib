from typing import Union

from fastapi import APIRouter, Depends, Query
from niagads.open_access_api_common.config.constants import SharedOpenAPITags
from niagads.open_access_api_common.models.features.bed import BEDResponse
from niagads.open_access_api_common.models.records.track.track import (
    TrackResponse,
    AbridgedTrackResponse,
)
from niagads.open_access_api_common.models.response.core import (
    RecordResponse,
    ListResponse,
)
from niagads.open_access_api_common.parameters.location import loc_param
from niagads.open_access_api_common.parameters.pagination import page_param
from niagads.open_access_api_common.parameters.record.path import track_param
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
from niagads.open_access_api_common.views.table import TableViewResponse
from niagads.open_access_filer_api.dependencies import (
    InternalRequestParameters,
)
from niagads.open_access_filer_api.documentation import BASE_TAGS
from niagads.open_access_filer_api.services.route import FILERRouteHelper

router = APIRouter(prefix="/record/track", tags=BASE_TAGS)


@router.get(
    "/",
    response_model=Union[
        TrackResponse,
        AbridgedTrackResponse,
        TableViewResponse,
        RecordResponse,
        ListResponse,
    ],
    summary="get-track-metadata-by-id-bulk",
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
):

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
                    if rContent == ResponseContent.BRIEF
                    else (
                        ListResponse
                        if rContent == ResponseContent.URLS
                        else RecordResponse
                    )
                )
            ),
        ),
        Parameters(track=track),
    )
    return await helper.get_track_metadata()


@router.get(
    "/{track}",
    tags=[str(SharedOpenAPITags.TRACK_RECORD)],
    response_model=Union[AbridgedTrackResponse, TrackResponse, RecordResponse],
    summary="get-track-metadata",
    description="retrieve track metadata for the FILER record identified by the `track` specified in the path; use `content=summary` for a brief response",
)
async def get_track_metadata(
    track=Depends(track_param),
    content: str = Query(
        ResponseContent.BRIEF,
        description=ResponseContent.descriptive(description=True),
    ),
    format: str = Query(
        ResponseFormat.JSON, description=ResponseFormat.generic(description=True)
    ),
    internal: InternalRequestParameters = Depends(),
) -> Union[AbridgedTrackResponse, TrackResponse, RecordResponse]:

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
                else AbridgedTrackResponse
            ),
        ),
        Parameters(track=track),
    )

    return await helper.get_track_metadata()


tags = [str(SharedOpenAPITags.TRACK_DATA)]


@router.get(
    "/{track}/data",
    tags=tags,
    summary="get-track-data",
    response_model=Union[
        BEDResponse, AbridgedTrackResponse, TableViewResponse, RecordResponse
    ],
    description="retrieve functional genomics track data from FILER in the specified region; specify `content=counts` to just retrieve a count of the number of hits in the specified region",
)
async def get_track_data(
    track=Depends(track_param),
    span: str = Depends(loc_param),
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
) -> Union[BEDResponse, AbridgedTrackResponse, TableViewResponse, RecordResponse]:

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
                    AbridgedTrackResponse
                    if rContent == ResponseContent.BRIEF
                    else RecordResponse
                )
            ),
        ),
        Parameters(track=track, span=span, page=page),
    )

    return await helper.get_track_data()
