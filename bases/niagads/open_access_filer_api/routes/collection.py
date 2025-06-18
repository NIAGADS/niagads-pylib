from fastapi import APIRouter, Depends, Query
from typing import Union

from niagads.database.models.metadata.composite_attributes import TrackDataStore
from niagads.open_access_api_common.config.constants import SharedOpenAPITags
from niagads.open_access_api_common.models.records.track.collection import (
    CollectionResponse,
)
from niagads.open_access_api_common.models.records.track.track import (
    TrackResponse,
    AbridgedTrackResponse,
)
from niagads.open_access_api_common.models.response.core import GenericResponse
from niagads.open_access_api_common.models.views.table.core import TableViewResponse
from niagads.open_access_api_common.parameters.pagination import page_param
from niagads.open_access_api_common.parameters.record.path import collection_param
from niagads.open_access_api_common.parameters.record.query import track_param
from niagads.open_access_api_common.parameters.response import (
    ResponseContent,
    ResponseFormat,
    ResponseView,
)
from niagads.open_access_api_common.services.metadata.query import MetadataQueryService
from niagads.open_access_api_common.services.route import (
    Parameters,
    ResponseConfiguration,
)
from niagads.open_access_filer_api.dependencies import InternalRequestParameters
from niagads.open_access_filer_api.documentation import BASE_TAGS
from niagads.open_access_filer_api.services.route import FILERRouteHelper


router = APIRouter(
    prefix="/collection",
    tags=BASE_TAGS
    + [
        str(SharedOpenAPITags.TRACK_RECORD),
        str(SharedOpenAPITags.COLLECTIONS),
    ],
)


@router.get(
    "/",
    response_model=CollectionResponse,
    summary="get-collections",
    description="Retrieve a full listing of FILER track collections.  Collections are curated lists of related data tracks.  Collections may associate tracks from a single study or experiment, by shared cohort or consortium or by application.",
)
async def get_collections(
    format: str = Query(
        ResponseFormat.JSON, description=ResponseFormat.generic(description=True)
    ),
    internal: InternalRequestParameters = Depends(),
) -> CollectionResponse:

    helper = FILERRouteHelper(
        internal,
        ResponseConfiguration(
            format=ResponseFormat.generic().validate(format, "format", ResponseFormat),
            content=ResponseContent.FULL,
            model=CollectionResponse,
        ),
        Parameters(),
    )

    result = await MetadataQueryService(
        internal.session, dataStore=[TrackDataStore.FILER, TrackDataStore.SHARED]
    ).get_collections()
    return await helper.generate_response(result)


@router.get(
    "/{collection}",
    response_model=Union[
        GenericResponse, AbridgedTrackResponse, TrackResponse, TableViewResponse
    ],
    summary="get-collection-record-metadata",
    description="Get the metadata for all tracks associated with a FILER collection.",
)
async def get_collection_track_metadata(
    collection: str = Depends(collection_param),
    track: str = Depends(track_param),
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
                    if rContent == ResponseContent.BRIEF
                    else GenericResponse
                )
            ),
        ),
        Parameters(collection=collection, page=page, track=track),
    )

    return await helper.get_collection_track_metadata()
