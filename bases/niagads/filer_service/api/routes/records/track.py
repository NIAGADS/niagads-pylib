from typing import Union

from fastapi import APIRouter, Depends, Query

from niagads.api.common.constants import SharedOpenAPITags
from niagads.api.common.models.domain.parameters.entity import (
    multi_track_id_query_param,
    track_id,
)
from niagads.api.common.models.domain.parameters.location import loc_param
from niagads.api.common.models.domain.parameters.response.content import (
    DefaultRFormatParam,
    DefaultRContentParam,
    RContentParamNoCounts,
)

from niagads.api.common.models.domain.parameters.response.pagination import page_param
from niagads.api.common.models.domain.parameters.types import (
    ResponseContent,
    ResponseFormat,
)
from niagads.api.common.models.response.base import DataResponse, ListResponse
from niagads.api.common.models.response.entities.dataset import (
    TrackMetadataResponse,
)
from niagads.api.common.models.response.entities.features.bed import BEDResponse
from niagads.api.common.services.metadata.query import TrackDatabase
from niagads.api.common.services.route import (
    RequestParameters,
    ResponseConfiguration,
)
from niagads.filer_service.api.dependencies import FILEREndpointRequestParameters
from niagads.filer_service.api.services.route import FILEREndpointService

router = APIRouter(
    prefix="/record/track",
    tags=["Records", "Tracks", str(SharedOpenAPITags.ENTITY_LOOKUP)],
)


@router.get(
    "/",
    response_model=TrackMetadataResponse,
    summary="get-track-metadata-bulk",
    description=(
        "Retrieve full metadata for one or more FILER track " "records by identifier."
    ),
)
async def get_track_metadata_bulk(
    track_ids: list[str] = Depends(multi_track_id_query_param),
    content: DefaultRContentParam = Query(
        ResponseContent.FULL,
        description=DefaultRContentParam.description(),
    ),
    format: DefaultRFormatParam = Query(
        ResponseFormat.JSON,
        description=DefaultRFormatParam.description(),
    ),
    internal: FILEREndpointRequestParameters = Depends(),
):
    response_content = DefaultRContentParam.validate(content)
    response_config = ResponseConfiguration(
        format=DefaultRFormatParam.validate(format),
        content=response_content,
        model=TrackMetadataResponse,
    )
    params = RequestParameters(track=track_ids)
    service = FILEREndpointService(internal, response_config, params)
    return await service.get_track_metadata()


@router.get(
    "/{track_id}",
    response_model=Union[TrackMetadataResponse, ListResponse],
    summary="get-track-metadata",
    description=(
        "Retrieve track metadata for the FILER record "
        "identified by the track specified in the path."
    ),
    response_model_exclude_none=True,
)
async def get_track_metadata(
    track_id: str = Depends(track_id),
    content: RContentParamNoCounts = Query(
        ResponseContent.FULL,
        description=RContentParamNoCounts.description(),
    ),
    format: DefaultRFormatParam = Query(
        ResponseFormat.JSON,
        description=DefaultRFormatParam.description(),
    ),
    internal: FILEREndpointRequestParameters = Depends(),
) -> Union[TrackMetadataResponse, ListResponse]:
    response_content = RContentParamNoCounts.validate(content)
    response_format = DefaultRFormatParam.validate(
        format,
    )
    response_config = ResponseConfiguration(
        content=response_content,
        format=response_format,
        model=(
            ListResponse
            if response_content in [ResponseContent.IDS, ResponseContent.URLS]
            else TrackMetadataResponse
        ),
    )
    params = RequestParameters(track=track_id)
    service = FILEREndpointService(internal, response_config, params)
    return await service.get_track_metadata()


@router.get(
    "/{track_id}/data",
    summary="get-track-data",
    response_model=Union[BEDResponse, DataResponse],
    description=(
        "Retrieve functional genomics track data from FILER " "in the specified region."
    ),
    tags=["Records", "Tracks", str(SharedOpenAPITags.DATA)],
)
async def get_track_data(
    track_id: str = Depends(track_id),
    span: str = Depends(loc_param),
    page: int = Depends(page_param),
    content: DefaultRContentParam = Query(
        ResponseContent.FULL,
        description=DefaultRContentParam.description(),
    ),
    format: DefaultRFormatParam = Query(
        ResponseFormat.JSON,
        description=DefaultRFormatParam.description(),
    ),
    internal: FILEREndpointRequestParameters = Depends(),
) -> Union[BEDResponse, DataResponse]:
    response_content = DefaultRContentParam.validate(content)
    response_format = DefaultRFormatParam.validate(
        format,
    )
    response_config = ResponseConfiguration(
        content=response_content,
        format=response_format,
        model=(
            BEDResponse if response_content == ResponseContent.FULL else DataResponse
        ),
    )
    params = RequestParameters(track=track_id, span=span, page=page)
    service = FILEREndpointService(internal, response_config, params)
    return await service.get_track_data()
