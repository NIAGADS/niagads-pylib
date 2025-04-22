from fastapi import APIRouter, Depends, Query
from typing import Union

from api.common.enums.database import DataStore
from api.common.enums.response_properties import (
    ResponseContent,
    ResponseFormat,
    ResponseView,
)
from api.common.exceptions import RESPONSES
from api.common.helpers import Parameters, ResponseConfiguration

from api.common.services.metadata_query import MetadataQueryService
from api.dependencies.parameters.identifiers import (
    optional_query_track_id_single,
    path_collection_name,
)
from api.dependencies.parameters.optional import page_param

from api.models.base_response_models import ResponseModel
from api.models.collection import CollectionResponse
from api.models.view_models import TableViewResponse

from api.routes.genomics.common.helpers import GenomicsRouteHelper
from api.routes.genomics.dependencies.parameters import InternalRequestParameters
from api.routes.genomics.models.genomics_track import (
    GenomicsTrackResponse,
    GenomicsTrackSummaryResponse,
)
from api.routes.genomics.queries.track_metadata import (
    CollectionQuery,
    CollectionTrackMetadataQuery,
)


router = APIRouter(prefix="/collection", tags=["Collections"], responses=RESPONSES)


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
        internal.session, dataStore=[DataStore.GENOMICS, DataStore.SHARED]
    ).get_collections()
    return await helper.generate_response(result)


@router.get(
    "/{collection}",
    response_model=Union[
        ResponseModel,
        GenomicsTrackSummaryResponse,
        GenomicsTrackResponse,
        TableViewResponse,
    ],
    name="Get track metadata by collection",
    description="retrieve full metadata for FILER track records associated with a collection",
)
async def get_collection_track_metadata(
    collection: str = Depends(path_collection_name),
    track: str = Depends(optional_query_track_id_single),
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
    ResponseModel,
    GenomicsTrackSummaryResponse,
    GenomicsTrackResponse,
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
                GenomicsTrackResponse
                if rContent == ResponseContent.FULL
                else (
                    GenomicsTrackSummaryResponse
                    if rContent == ResponseContent.SUMMARY
                    else ResponseModel
                )
            ),
        ),
        Parameters(collection=collection, page=page, track=track),
    )

    return await helper.get_collection_track_metadata()
