from typing import Union

from fastapi import APIRouter, Depends, Query
from niagads.api.common.constants import SharedOpenAPITags
from niagads.api.common.models.datasets.collection import CollectionResponse
from niagads.api.common.models.datasets.track import (
    AbridgedTrackResponse,
    TrackResponse,
)
from niagads.api.common.models.response.core import RecordResponse
from niagads.api.common.parameters.pagination import page_param
from niagads.api.common.parameters.record.path import collection_param
from niagads.api.common.parameters.record.query import track_param
from niagads.api.common.parameters.response import (
    ResponseContent,
    ResponseFormat,
    ResponseView,
)
from niagads.api.common.services.metadata.query import MetadataQueryService
from niagads.api.common.services.route import Parameters, ResponseConfiguration
from niagads.api.common.views.table import TableViewResponse
from niagads.api.filer.dependencies import InternalRequestParameters
from niagads.api.filer.documentation import BASE_TAGS
from niagads.api.filer.services.route import FILERRouteHelper
from niagads.database.mixins.datasets.track import TrackDataStore

router = APIRouter(
    prefix="/collection",
    tags=BASE_TAGS + [str(SharedOpenAPITags.ENTITY_LOOKUP)],
)


@router.get(
    "/",
    response_model=CollectionResponse,
    summary="get-collections",
    description=(
        "Retrieve a full listing of FILER track collections. "
        "Collections are curated lists of related data tracks. "
        "Collections may associate tracks from a single study or experiment, "
        "by shared cohort or consortium or by application."
    ),
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
        internal.session, data_store=[TrackDataStore.FILER, TrackDataStore.SHARED]
    ).get_collections()
    return await helper.generate_response(result)


@router.get(
    "/{collection}",
    response_model=Union[
        RecordResponse, AbridgedTrackResponse, TrackResponse, TableViewResponse
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
) -> Union[RecordResponse, AbridgedTrackResponse, TrackResponse, TableViewResponse]:

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
        Parameters(collection=collection, page=page, track=track),
    )

    return await helper.get_collection_track_metadata()
