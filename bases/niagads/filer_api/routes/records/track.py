from typing import Union

from fastapi import APIRouter, Depends, Query
from niagads.api.common.constants import SharedOpenAPITags
from niagads.api.common.models.domain.parameters.entity import (
    multi_track_id_query_param,
    track_id,
)
from niagads.api.common.models.domain.parameters.location import loc_param
from niagads.api.common.models.domain.parameters.response.pagination import page_param
from niagads.api.common.models.domain.parameters.response.view import (
    DataQueryResponseViewEnumParam,
    RContentParamNoCounts,
    ResponseFormatEnumParam,
    ResponseViewEnumParam,
)
from niagads.api.common.models.domain.parameters.types import (
    ResponseFormat,
    ResponseView,
)
from niagads.api.common.models.response.base import (
    CountResponse,
    ListResponse,
)
from niagads.api.common.models.response.entities.dataset import (
    TrackMetadataResponse,
)
from niagads.api.common.models.response.entities.features.bed import BEDResponse
from niagads.api.common.services.route import (
    RequestParameters,
    ResponseConfiguration,
)
from niagads.filer_api.dependencies import FILEREndpointRequestParameters
from niagads.filer_api.services.route import FILEREndpointService

router = APIRouter(
    prefix="/record/track",
    tags=["Records", "Tracks", str(SharedOpenAPITags.ENTITY_LOOKUP)],
)


@router.get(
    "/",
    response_model=Union[TrackMetadataResponse, ListResponse, CountResponse],
    response_model_exclude_none=True,
    summary="get-track-metadata-bulk",
    description="Retrieve full metadata for one or more FILER track records by identifier.",
)
async def get_track_metadata_bulk(
    track_ids: list[str] = Depends(multi_track_id_query_param),
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
    params = RequestParameters(track=track_ids)
    service = FILEREndpointService(internal, response_config, params)
    return await service.get_track_metadata()


@router.get(
    "/{track_id}",
    response_model=Union[TrackMetadataResponse, ListResponse],
    response_model_exclude_none=True,
    summary="get-track-metadata",
    description=(
        "Retrieve track metadata for the FILER record "
        "identified by the track identifier specified in the query path."
    ),
)
async def get_track_metadata(
    track_id: str = Depends(track_id),
    content: RContentParamNoCounts = Query(
        ResponseView.FULL,
        description=RContentParamNoCounts.description(),
    ),
    format: ResponseFormatEnumParam = Query(
        ResponseFormat.JSON,
        description=ResponseFormatEnumParam.description(),
    ),
    internal: FILEREndpointRequestParameters = Depends(),
) -> Union[TrackMetadataResponse, ListResponse]:
    response_content = RContentParamNoCounts.validate(content)
    response_format = ResponseFormatEnumParam.validate(
        format,
    )
    response_config = ResponseConfiguration(
        content=response_content,
        format=response_format,
        model=(
            ListResponse
            if response_content in [ResponseView.IDS, ResponseView.URLS]
            else TrackMetadataResponse
        ),
    )
    params = RequestParameters(track=track_id)
    service = FILEREndpointService(internal, response_config, params)
    return await service.get_track_metadata()


@router.get(
    "/{track_id}/data",
    summary="get-track-data",
    response_model=Union[BEDResponse, CountResponse],
    description=(
        "Retrieve track data from the FILER track specified in the query path, within a the specific genomic region."
    ),
    tags=["Records", "Tracks", str(SharedOpenAPITags.DATA)],
)
async def get_track_data(
    track_id: str = Depends(track_id),
    span: str = Depends(loc_param),
    page: int = Depends(page_param),
    content: DataQueryResponseViewEnumParam = Query(
        ResponseView.FULL,
        description=DataQueryResponseViewEnumParam.description(),
    ),
    format: ResponseFormatEnumParam = Query(
        ResponseFormat.JSON,
        description=ResponseFormatEnumParam.description(),
    ),
    internal: FILEREndpointRequestParameters = Depends(),
) -> Union[BEDResponse, CountResponse]:
    response_content = DataQueryResponseViewEnumParam.validate(content)
    response_format = ResponseFormatEnumParam.validate(
        format,
    )
    response_config = ResponseConfiguration(
        content=response_content,
        format=response_format,
        model=(BEDResponse if response_content == ResponseView.FULL else CountResponse),
    )
    params = RequestParameters(track=track_id, span=span, page=page)
    service = FILEREndpointService(internal, response_config, params)
    return await service.get_track_data()
