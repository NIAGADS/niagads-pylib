from typing import Union

from fastapi import APIRouter, Depends, Query
from niagads.exceptions.core import ValidationError
from niagads.genome.core import Assembly
from niagads.open_access_api_common.config.constants import SharedOpenAPITags
from niagads.open_access_api_common.models.records.track.track import (
    AbridgedTrackResponse,
    TrackResponse,
)
from niagads.open_access_api_common.models.response.core import GenericResponse
from niagads.open_access_api_common.models.views.table.core import TableViewResponse
from niagads.open_access_api_common.parameters.location import (
    assembly_param,
    chromosome_param,
    span_param,
)
from niagads.open_access_api_common.parameters.pagination import page_param
from niagads.open_access_api_common.parameters.record.path import track_param
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
from niagads.open_access_filer_api.documentation import BASE_TAGS
from niagads.open_access_filer_api.services.route import FILERRouteHelper

router = APIRouter(
    prefix="/metadata",
    tags=BASE_TAGS + [str(SharedOpenAPITags.TRACK_RECORD)],
)


@router.get(
    "/",
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


tags = [str(SharedOpenAPITags.RECORD_SEARCH)]


@router.get(
    "/search",
    tags=tags,
    response_model=Union[
        GenericResponse,
        AbridgedTrackResponse,
        TrackResponse,
        TableViewResponse,
    ],
    summary="search-track-records",
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
) -> Union[GenericResponse, AbridgedTrackResponse, TrackResponse, TableViewResponse]:

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
                    AbridgedTrackResponse
                    if rContent == ResponseContent.SUMMARY
                    else GenericResponse
                )
            ),
        ),
        Parameters(page=page, assembly=assembly, filter=filter, keyword=keyword),
    )

    return await helper.search_track_metadata()


@router.get(
    "/shard/{track}",
    tags=tags,
    response_model=Union[TrackResponse, AbridgedTrackResponse, GenericResponse],
    summary="get-shard-metadata-beta",
    description="Some tracks are sharded by chromosome.  Use this query to find a shard-specific track given a chromosome and related track identifier.",
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
) -> Union[AbridgedTrackResponse, TrackResponse, GenericResponse]:

    rContent = ResponseContent.descriptive(inclUrls=True).validate(
        content, "content", ResponseContent
    )
    helper = FILERRouteHelper(
        internal,
        ResponseConfiguration(
            format=ResponseFormat.generic().validate(format, "format", ResponseFormat),
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
        Parameters(track=track, chromosome=chr),
    )

    return await helper.get_shard()
