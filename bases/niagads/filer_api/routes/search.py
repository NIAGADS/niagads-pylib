from typing import Union

from fastapi import APIRouter, Depends, Query
from niagads.exceptions.core import ValidationError
from niagads.assembly.core import Assembly
from niagads.api_common.constants import SharedOpenAPITags
from niagads.api_common.models.response.core import RecordResponse
from niagads.api_common.models.datasets.track import (
    AbridgedTrackResponse,
    TrackResponse,
)
from niagads.api_common.parameters.location import (
    assembly_param,
    chromosome_param,
)
from niagads.api_common.parameters.pagination import page_param
from niagads.api_common.parameters.record.path import track_param
from niagads.api_common.parameters.response import (
    ResponseContent,
    ResponseFormat,
    ResponseView,
)
from niagads.api_common.parameters.text_search import keyword_param
from niagads.api_common.services.route import (
    Parameters,
    ResponseConfiguration,
)
from niagads.api_common.views.table import TableViewResponse
from niagads.filer_api.dependencies import (
    TEXT_FILTER_PARAMETER,
    InternalRequestParameters,
)
from niagads.filer_api.documentation import BASE_TAGS
from niagads.filer_api.services.route import FILERRouteHelper

router = APIRouter(
    prefix="/search",
    tags=BASE_TAGS + [str(SharedOpenAPITags.SEARCH)],
)


@router.get(
    "/",
    response_model=Union[
        RecordResponse,
        AbridgedTrackResponse,
        TrackResponse,
        TableViewResponse,
    ],
    summary="search-track-records",
    description="find functional genomics tracks by a keyword search against all text fields in the track metadata",
    # description="find functional genomics tracks using category filters
    # or by a keyword search against all text fields in the track metadata",
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
) -> Union[RecordResponse, AbridgedTrackResponse, TrackResponse, TableViewResponse]:

    if filter is None and keyword is None:
        raise ValidationError(
            "must specify either a `filter` and/or a `keyword` to search"
        )

    response_content = ResponseContent.validate(content, "content", ResponseContent)
    helper = FILERRouteHelper(
        internal,
        ResponseConfiguration(
            format=ResponseFormat.generic().validate(format, "format", ResponseFormat),
            content=response_content,
            view=ResponseView.table().validate(view, "view", ResponseView),
            model=(
                TrackResponse
                if response_content == ResponseContent.FULL
                else (
                    AbridgedTrackResponse
                    if response_content == ResponseContent.BRIEF
                    else RecordResponse
                )
            ),
        ),
        Parameters(page=page, assembly=assembly, filter=filter, keyword=keyword),
    )

    return await helper.search_track_metadata()


@router.get(
    "/shard/{track}",
    response_model=Union[TrackResponse, AbridgedTrackResponse, RecordResponse],
    summary="get-shard-metadata-beta",
    description=(
        "Some tracks are sharded by chromosome. "
        "Use this query to find a shard-specific track given a chromosome and related track identifier."
    ),
    include_in_schema=False,
)
async def get_shard(
    track: str = Depends(track_param),
    chr: str = Depends(chromosome_param),
    content: str = Query(
        ResponseContent.FULL,
        description=ResponseContent.descriptive(inclUrls=True, description=True),
    ),
    format: str = Query(
        ResponseFormat.JSON, description=ResponseFormat.generic(description=True)
    ),
    internal: InternalRequestParameters = Depends(),
) -> Union[AbridgedTrackResponse, TrackResponse, RecordResponse]:

    response_content = ResponseContent.descriptive(inclUrls=True).validate(
        content, "content", ResponseContent
    )
    helper = FILERRouteHelper(
        internal,
        ResponseConfiguration(
            format=ResponseFormat.generic().validate(format, "format", ResponseFormat),
            content=response_content,
            model=(
                TrackResponse
                if response_content == ResponseContent.FULL
                else (
                    AbridgedTrackResponse
                    if response_content == ResponseContent.BRIEF
                    else RecordResponse
                )
            ),
        ),
        Parameters(track=track, chromosome=chr),
    )

    return await helper.get_shard()
