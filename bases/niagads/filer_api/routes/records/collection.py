from typing import Union

from fastapi import APIRouter, Depends, Query
from niagads.api.common.models.domain.parameters.entity import collection_id
from niagads.api.common.models.domain.parameters.response.view import (
    ResponseFormatEnumParam,
    ResponseViewEnumParam,
)
from niagads.api.common.models.domain.parameters.types import (
    ResponseFormat,
    ResponseView,
)
from niagads.api.common.models.response.base import CountResponse, ListResponse
from niagads.api.common.models.response.entities.dataset import (
    TrackCollectionResponse,
    TrackMetadataResponse,
)
from niagads.api.common.services.route import RequestParameters, ResponseConfiguration
from niagads.filer_api.dependencies import FILEREndpointRequestParameters
from niagads.filer_api.services.route import FILEREndpointService

router = APIRouter(prefix="/record/collection", tags=["Records", "Collections"])


@router.get(
    "/",
    response_model=TrackCollectionResponse,
    summary="get-collections",
    description="List all available FILER track collections.",
)
async def get_collections(
    format: ResponseFormatEnumParam = Query(
        ResponseFormat.JSON,
        description=ResponseFormatEnumParam.description(),
    ),
    internal: FILEREndpointRequestParameters = Depends(),
) -> TrackCollectionResponse:

    response_config = ResponseConfiguration(
        content=ResponseView.FULL,
        format=ResponseFormatEnumParam.validate(format),
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
    format: ResponseFormatEnumParam = Query(
        ResponseFormat.JSON,
        description=ResponseFormatEnumParam.description(),
    ),
    internal: FILEREndpointRequestParameters = Depends(),
) -> TrackCollectionResponse:
    response_config = ResponseConfiguration(
        content=ResponseView.FULL,
        format=ResponseFormatEnumParam.validate(format),
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
    content: ResponseViewEnumParam = Query(
        ResponseView.FULL,
        description=ResponseViewEnumParam.description(),
    ),
    format: ResponseFormatEnumParam = Query(
        ResponseFormat.JSON,
        description=ResponseFormatEnumParam.description(),
    ),
    internal: FILEREndpointRequestParameters = Depends(),
) -> Union[TrackMetadataResponse, ListResponse]:
    response_content = ResponseViewEnumParam.validate(content)
    response_format = ResponseFormatEnumParam.validate(format)
    response_config = ResponseConfiguration(
        format=response_format,
        content=response_content,
        model=(
            ListResponse
            if response_content in [ResponseView.IDS, ResponseView.URLS]
            else (
                CountResponse
                if response_content == ResponseView.COUNTS
                else TrackMetadataResponse
            )
        ),
    )
    params = RequestParameters(collection_id=collection_id)
    service = FILEREndpointService(internal, response_config, params)
    return await service.get_collection_track_metadata()
