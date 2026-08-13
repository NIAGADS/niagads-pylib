from typing import Union
from fastapi import APIRouter, Depends, Query
from niagads.filer_api.dependencies import FILEREndpointRequestParameters
from niagads.filer_api.services.route import FILEREndpointService

from niagads.api.common.models.domain.parameters.entity import collection_id
from niagads.api.common.models.domain.parameters.response.content import (
    DefaultRContentParam,
    DefaultRFormatParam,
)
from niagads.api.common.models.domain.parameters.types import (
    ResponseContent,
    ResponseFormat,
)
from niagads.api.common.models.response.base import CountResponse, ListResponse
from niagads.api.common.models.response.entities.dataset import (
    TrackCollectionResponse,
    TrackMetadataResponse,
)
from niagads.api.common.services.route import RequestParameters, ResponseConfiguration

router = APIRouter(prefix="/record/collection", tags=["Records", "Collections"])


@router.get(
    "/",
    response_model=TrackCollectionResponse,
    summary="get-collections",
    description="List all available FILER track collections.",
)
async def get_collections(
    format: DefaultRFormatParam = Query(
        ResponseFormat.JSON,
        description=DefaultRFormatParam.description(),
    ),
    internal: FILEREndpointRequestParameters = Depends(),
) -> TrackCollectionResponse:

    response_config = ResponseConfiguration(
        content=ResponseContent.FULL,
        format=DefaultRFormatParam.validate(format),
        model=TrackCollectionResponse,
    )

    service = FILEREndpointService(internal, response_config)
    return await service.get_collections()


@router.get(
    "/{collection_id}",
    response_model=TrackCollectionResponse,
    summary="get-collection-record",
    description="Retrieve metadata summary for a FILER collection record",
)
async def get_collection(
    collection_id: str = Depends(collection_id),
    format: DefaultRFormatParam = Query(
        ResponseFormat.JSON,
        description=DefaultRFormatParam.description(),
    ),
    internal: FILEREndpointRequestParameters = Depends(),
) -> TrackCollectionResponse:
    response_config = ResponseConfiguration(
        content=ResponseContent.FULL,
        format=DefaultRFormatParam.validate(format),
        model=TrackCollectionResponse,
    )
    params = RequestParameters(collection_id=collection_id)
    service = FILEREndpointService(internal, response_config, params)
    return await service.get_collections()


@router.get(
    "/{collection}/tracks",
    response_model=Union[TrackMetadataResponse, ListResponse, CountResponse],
    response_model_exclude_none=True,
    summary="get-collection-tracks",
    description="Retrieve track metadata for all tracks associatiated with a FILER collection record",
)
async def get_collection_record(
    collection_id: str = Depends(collection_id),
    content: DefaultRContentParam = Query(
        ResponseContent.FULL,
        description=DefaultRContentParam.description(),
    ),
    format: DefaultRFormatParam = Query(
        ResponseFormat.JSON,
        description=DefaultRFormatParam.description(),
    ),
    internal: FILEREndpointRequestParameters = Depends(),
) -> Union[TrackMetadataResponse, ListResponse]:
    response_content = DefaultRContentParam.validate(content)
    response_format = DefaultRFormatParam.validate(format)
    response_config = ResponseConfiguration(
        format=response_format,
        content=response_content,
        model=(
            ListResponse
            if response_content in [ResponseContent.IDS, ResponseContent.URLS]
            else (
                CountResponse
                if response_content == ResponseContent.COUNTS
                else TrackMetadataResponse
            )
        ),
    )
    params = RequestParameters(collection_id=collection_id)
    service = FILEREndpointService(internal, response_config, params)
    return await service.get_collection_track_metadata()
