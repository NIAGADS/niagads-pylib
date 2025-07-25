from typing import Union

from fastapi import APIRouter, Depends, Query
from niagads.database.schemas.dataset.track import TrackDataStore
from niagads.api_common.constants import SharedOpenAPITags
from niagads.api_common.models.response.core import RecordResponse
from niagads.api_common.models.datasets.collection import CollectionResponse
from niagads.api_common.models.datasets.track import (
    AbridgedTrackResponse,
    TrackResponse,
)
from niagads.api_common.parameters.pagination import page_param
from niagads.api_common.parameters.record.path import collection_param
from niagads.api_common.parameters.record.query import optional_track_param
from niagads.api_common.parameters.response import (
    ResponseContent,
    ResponseFormat,
    ResponseView,
)
from niagads.api_common.services.metadata.query import MetadataQueryService
from niagads.api_common.services.route import (
    Parameters,
    ResponseConfiguration,
)
from niagads.api_common.views.table import TableViewResponse
from niagads.genomics_api.dependencies import InternalRequestParameters
from niagads.genomics_api.documentation import APP_NAME
from niagads.genomics_api.services.route import GenomicsRouteHelper

router = APIRouter(
    prefix="/record/collection",
    tags=[
        APP_NAME,
        str(SharedOpenAPITags.ENTITY_LOOKUP),
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
        internal.session, data_store=[TrackDataStore.GENOMICS, TrackDataStore.SHARED]
    ).get_collections()
    return await helper.generate_response(result)


@router.get(
    "/{collection}",
    response_model=Union[
        RecordResponse,
        AbridgedTrackResponse,
        TrackResponse,
        TableViewResponse,
    ],
    name="Get track metadata by collection",
    description="retrieve full metadata for collection track records",
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
    RecordResponse,
    AbridgedTrackResponse,
    TrackResponse,
    TableViewResponse,
]:

    response_content = ResponseContent.validate(content, "content", ResponseContent)
    helper = GenomicsRouteHelper(
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
