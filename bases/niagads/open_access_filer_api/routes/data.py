from typing import Union

from fastapi import APIRouter, Depends, Query
from niagads.genome.core import Assembly
from niagads.open_access_api_common.constants import SharedOpenAPITags

from niagads.open_access_api_common.models.features.bed import BEDResponse
from niagads.open_access_api_common.models.response.core import RecordResponse

from niagads.open_access_api_common.models.tracks.track import AbridgedTrackResponse
from niagads.open_access_api_common.parameters.location import (
    assembly_param,
    span_param,
)
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
from niagads.open_access_api_common.views.table import TableViewResponse
from niagads.open_access_filer_api.dependencies import (
    TEXT_FILTER_PARAMETER,
    InternalRequestParameters,
)
from niagads.open_access_filer_api.documentation import BASE_TAGS
from niagads.open_access_filer_api.services.route import FILERRouteHelper

router = APIRouter(
    prefix="/data",
    tags=BASE_TAGS + [str(SharedOpenAPITags.TRACK_DATA)],
)


@router.get(
    "/",
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

    response_content = ResponseContent.data().validate(
        content, "content", ResponseContent
    )
    helper = FILERRouteHelper(
        internal,
        ResponseConfiguration(
            format=ResponseFormat.functional_genomics().validate(
                format, "format", ResponseFormat
            ),
            content=response_content,
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


tags = [str(SharedOpenAPITags.RECORD_SEARCH)]


@router.get(
    "/search",
    tags=tags,
    response_model=Union[
        RecordResponse, AbridgedTrackResponse, BEDResponse, TableViewResponse
    ],
    summary="get-track-data-by-metadata-search",
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
) -> Union[RecordResponse, AbridgedTrackResponse, BEDResponse, TableViewResponse]:

    response_content = ResponseContent.data().validate(
        content, "content", ResponseContent
    )
    helper = FILERRouteHelper(
        internal,
        ResponseConfiguration(
            format=ResponseFormat.functional_genomics().validate(
                format, "format", ResponseFormat
            ),
            content=response_content,
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
        Parameters(
            assembly=assembly, filter=filter, keyword=keyword, span=span, page=page
        ),
    )

    return await helper.search_track_data()
