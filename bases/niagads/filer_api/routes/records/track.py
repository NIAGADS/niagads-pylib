from typing import Union

from fastapi import APIRouter, Depends, Query
from niagads.api_common.constants import SharedOpenAPITags
from niagads.api_common.models.features.bed import BEDResponse
from niagads.api_common.models.response.core import (
    RecordResponse,
    ListResponse,
)
from niagads.api_common.models.datasets.track import (
    AbridgedTrackResponse,
    TrackResponse,
)
from niagads.api_common.parameters.location import loc_param
from niagads.api_common.parameters.pagination import page_param
from niagads.api_common.parameters.record.path import track_param
from niagads.api_common.parameters.record.query import track_list_param
from niagads.api_common.parameters.response import (
    ResponseContent,
    ResponseFormat,
    ResponseView,
)
from niagads.api_common.services.route import (
    Parameters,
    ResponseConfiguration,
)
from niagads.api_common.views.table import TableViewResponse
from niagads.filer_api.dependencies import (
    InternalRequestParameters,
)
from niagads.filer_api.documentation import BASE_TAGS
from niagads.filer_api.services.route import FILERRouteHelper

router = APIRouter(
    prefix="/record/track", tags=BASE_TAGS + [str(SharedOpenAPITags.ENTITY_LOOKUP)]
)


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

    response_content = ResponseContent.descriptive(inclUrls=True).validate(
        content, "content", ResponseContent
    )
    helper = FILERRouteHelper(
        internal,
        ResponseConfiguration(
            format=ResponseFormat.generic().validate(format, "format", ResponseFormat),
            view=ResponseView.table().validate(view, "view", ResponseView),
            content=response_content,
            model=(
                TrackResponse
                if response_content == ResponseContent.FULL
                else (
                    AbridgedTrackResponse
                    if response_content == ResponseContent.BRIEF
                    else (
                        ListResponse
                        if response_content == ResponseContent.URLS
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
    response_model=Union[AbridgedTrackResponse, TrackResponse, RecordResponse],
    summary="get-track-metadata",
    description=(
        "retrieve track metadata for the FILER record identified by the `track` specified in the path; "
        "use `content=summary` for a brief response"
    ),
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

    response_content = ResponseContent.descriptive().validate(
        content, "content", ResponseContent
    )
    response_format = ResponseFormat.generic().validate(
        format, "format", ResponseFormat
    )
    helper = FILERRouteHelper(
        internal,
        ResponseConfiguration(
            content=response_content,
            format=response_format,
            model=(
                TrackResponse
                if response_content == ResponseContent.FULL
                else AbridgedTrackResponse
            ),
        ),
        Parameters(track=track),
    )

    return await helper.get_track_metadata()


tags = [str(SharedOpenAPITags.DATA)]


@router.get(
    "/{track}/data",
    tags=tags,
    summary="get-track-data",
    response_model=Union[
        BEDResponse, AbridgedTrackResponse, TableViewResponse, RecordResponse
    ],
    description=(
        "retrieve functional genomics track data from FILER in the specified region; "
        "specify `content=counts` to just retrieve a count of the number of hits in the specified region"
    ),
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

    response_content = ResponseContent.data().validate(
        content, "content", ResponseContent
    )
    helper = FILERRouteHelper(
        internal,
        ResponseConfiguration(
            content=response_content,
            format=ResponseFormat.functional_genomics().validate(
                format, "format", ResponseFormat
            ),
            view=ResponseView.validate(view, "view", ResponseView),
            model=(
                BEDResponse
                if response_content == ResponseContent.FULL
                else (
                    AbridgedTrackResponse
                    if response_content == ResponseContent.BRIEF
                    else RecordResponse
                )
            ),
        ),
        Parameters(track=track, span=span, page=page),
    )

    return await helper.get_track_data()
