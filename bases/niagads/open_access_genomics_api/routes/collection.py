from typing import Union

from fastapi import APIRouter, Depends, Query
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
from niagads.open_access_api_common.parameters.record.query import optional_track_param
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
from niagads.open_access_genomics_api.dependencies import InternalRequestParameters
from niagads.open_access_genomics_api.documentation import APP_NAME
from niagads.open_access_genomics_api.services.route import GenomicsRouteHelper

router = APIRouter(
    prefix="/collection",
    tags=[
        APP_NAME,
        str(SharedOpenAPITags.TRACK_RECORD),
        str(SharedOpenAPITags.COLLECTIONS),
    ],
)


@router.get(
    "/",
    response_model=CollectionResponse,
    name="Get GenomicsDB Track Collections",
    description="list available collections of related GenomicsDB tracks",
)
async def get_collections(
    format: str = Query(
        ResponseFormat.JSON, description=ResponseFormat.generic(description=True)
    ),
    internal: InternalRequestParameters = Depends(),
) -> CollectionResponse:

    helper = GenomicsRouteHelper(
        internal,
        ResponseConfiguration(
            format=ResponseFormat.generic().validate(format, "format", ResponseFormat),
            content=ResponseContent.FULL,
            model=CollectionResponse,
        ),
        Parameters(),
    )

    result = await MetadataQueryService(
        internal.session, dataStore=[TrackDataStore.GENOMICS, TrackDataStore.SHARED]
    ).get_collections()
    return await helper.generate_response(result)


@router.get(
    "/{collection}",
    response_model=Union[
        GenericResponse,
        AbridgedTrackResponse,
        TrackResponse,
        TableViewResponse,
    ],
    name="Get track metadata by collection",
    description="retrieve full metadata for FILER track records associated with a collection",
)
async def get_collection_track_metadata(
    collection: str = Depends(collection_param),
    track: str = Depends(optional_track_param),
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
) -> Union[
    GenericResponse,
    AbridgedTrackResponse,
    TrackResponse,
    TableViewResponse,
]:

    rContent = ResponseContent.validate(content, "content", ResponseContent)
    helper = GenomicsRouteHelper(
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
