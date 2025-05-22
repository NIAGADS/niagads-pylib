from typing import List, Union
from fastapi import APIRouter, Depends, Query
from niagads.exceptions.core import ValidationError
from niagads.genome.core import Assembly
from niagads.open_access_api_common.models.records.track.igvbrowser import (
    IGVBrowserTrackConfig,
    IGVBrowserTrackConfigResponse,
    IGVBrowserTrackSelectorResponse,
)
from niagads.open_access_api_common.models.records.track.track import (
    TrackResponse,
    TrackSummaryResponse,
)
from niagads.open_access_api_common.models.response.core import ResponseModel
from niagads.open_access_api_common.models.views.table.core import TableViewModel
from niagads.open_access_api_common.parameters.location import (
    assembly_param,
    chromosome_param,
)
from niagads.open_access_api_common.parameters.record.path import query_collection_name
from niagads.open_access_api_common.parameters.record.query import (
    optional_track_list_param,
    track_param,
)
from niagads.open_access_api_common.parameters.response import (
    ResponseContent,
    ResponseFormat,
)
from niagads.open_access_api_common.services.metadata.query import MetadataQueryService
from niagads.open_access_api_common.services.route import (
    Parameters,
    ResponseConfiguration,
)
from niagads.open_access_filer_api.dependencies import (
    TRACK_DATA_STORES,
    InternalRequestParameters,
    TextSearchFilterFields,
)
from niagads.open_access_filer_api.documentation import ROUTE_NAME
from niagads.open_access_filer_api.services.route import FILERRouteHelper

router = APIRouter(prefix="/service", tags=[ROUTE_NAME, "Services"])

tags = ["NIAGADS Genome Browser"]


@router.get(
    "/igvbrowser/config",
    tags=tags,
    response_model=List[IGVBrowserTrackConfig],
    name="Get Genome Browser Configuration",
    description="retrieve NIAGADS Genome Browser track configuration for one or more FILER `track`(s) by ID or collection",
)
# , or keyword search")
async def get_track_browser_config(
    track=Depends(optional_track_list_param),
    assembly: Assembly = Depends(assembly_param),
    collection: str = Depends(query_collection_name),
    # keyword: str = Depends(keyword_param),
    internal: InternalRequestParameters = Depends(),
) -> List[IGVBrowserTrackConfig]:

    helper = FILERRouteHelper(
        internal,
        ResponseConfiguration(
            content=ResponseContent.FULL, model=IGVBrowserTrackConfigResponse
        ),
        Parameters(
            track=track, assembly=assembly, collection=collection
        ),  # , keyword=keyword)
    )

    setParamCount = sum(
        x is not None for x in [collection, track]
    )  # [collection, keyword, track])
    if setParamCount == 0 or setParamCount > 1:
        # FIXME: allow combinations
        raise ValidationError(
            "please provide a value for exactly one of `collection`  or `track`"
        )

    if collection is not None:
        result = await helper.get_collection_track_metadata()
    # elif keyword is not None:
    #    result = await helper.search_track_metadata()
    else:
        result = await helper.get_track_metadata()

    return result.data


@router.get(
    "/igvbrowser/selector",
    tags=tags,
    response_model=TableViewModel,
    name="Get Genome Browser Track Selector Table",
    description="retrieve NIAGADS Genome Browser track selector table for one or more FILER `track`(s) by ID or collection",
)
# , or keyword")
async def get_track_browser_config(
    track=Depends(optional_track_list_param),
    assembly: Assembly = Depends(assembly_param),
    collection: str = Depends(query_collection_name),
    # keyword: str = Depends(keyword_param),
    internal: InternalRequestParameters = Depends(),
) -> TableViewModel:

    helper = FILERRouteHelper(
        internal,
        ResponseConfiguration(
            content=ResponseContent.FULL, model=IGVBrowserTrackSelectorResponse
        ),
        Parameters(
            track=track, assembly=assembly, collection=collection
        ),  #  keyword=keyword)
    )

    setParamCount = sum(
        x is not None for x in [collection, track]
    )  # [collection, keyword, track])
    if setParamCount == 0 or setParamCount > 1:
        # FIXME: allow combinations
        raise ValidationError(
            "please provide a value for exactly one of `collection` or `track`"
        )

    if collection is not None:
        result = await helper.get_collection_track_metadata()
    # elif keyword is not None:
    #     result = await helper.search_track_metadata()
    else:
        result = await helper.get_track_metadata()

    return result.data


tags = ["Lookup Services"]


@router.get(
    "/lookup/shard",
    tags=tags,
    response_model=Union[TrackResponse, TrackSummaryResponse, ResponseModel],
    name="Get shard metadata",
    description="Some tracks are sharded by chromosome.  Use this query to find a shard-specific track given a chromosome and related track identifier.",
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
) -> Union[TrackSummaryResponse, TrackResponse, ResponseModel]:

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
                    TrackSummaryResponse
                    if rContent == ResponseContent.SUMMARY
                    else ResponseModel
                )
            ),
        ),
        Parameters(track=track, chromosome=chr),
    )

    return await helper.get_shard()


tags = tags + ["Service Information"]


@router.get(
    "/lookup/filters",
    tags=tags,
    response_model=Union[ResponseModel],
    name="Get text search filter fields",
    description="List allowable fields for text search filter expressions.",
)
async def get_allowable_text_filters(
    internal: InternalRequestParameters = Depends(),
) -> ResponseModel:

    return ResponseModel(
        data=TextSearchFilterFields.list(toLower=True), request=internal.requestData
    )
