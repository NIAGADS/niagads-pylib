from typing import Union

from fastapi import APIRouter, Depends, Query

from niagads.api.common.constants import SharedOpenAPITags
from niagads.api.common.models.domain.parameters.filters.text_search import (
    keyword_param,
)
from niagads.api.common.models.domain.parameters.location import (
    assembly_param,
    span_param,
)
from niagads.api.common.models.domain.parameters.response.types import (
    ResponseContent,
    ResponseFormat,
)
from niagads.api.common.models.domain.parameters.response.pagination import (
    page_param,
)
from niagads.api.common.models.response.base import DataResponse
from niagads.api.common.models.response.entities.dataset import (
    TrackMetadataResponse,
)
from niagads.api.common.models.response.entities.features.bed import BEDResponse
from niagads.api.common.services.route import (
    RequestParameters,
    ResponseConfiguration,
)
from niagads.exceptions.core import ValidationError
from niagads.filer_service.api.dependencies import (
    TEXT_FILTER_PARAMETER,
    FILEREndpointRequestParameters,
)
from niagads.filer_service.api.services.route import FILEREndpointService

router = APIRouter(
    prefix="/search",
    tags=["Search", str(SharedOpenAPITags.SEARCH)],
)


@router.get(
    "/tracks",
    response_model=TrackMetadataResponse,
    summary="search-track-records",
    description=("Search FILER track records using structured keywords and filters."),
)
async def search_tracks(
    filter=Depends(TEXT_FILTER_PARAMETER),
    keyword: str = Depends(keyword_param),
    genome_build: str = Depends(assembly_param),
    page: int = Depends(page_param),
    content: str = Query(
        ResponseContent.FULL,
        description=ResponseContent.entity_record(has_urls=True).description(),
    ),
    format: str = Query(
        ResponseFormat.JSON,
        description=DefaultResponseFormatParam.description(),
    ),
    internal: FILEREndpointRequestParameters = Depends(),
) -> TrackMetadataResponse:
    if filter is None and keyword is None:
        raise ValidationError(
            "must specify either a `filter` and/or a `keyword` to search"
        )

    response_content = ResponseContent.entity_record(has_urls=True).validate(content)
    response_config = ResponseConfiguration(
        format=ResponseFormat.validate(format),
        content=response_content,
        model=TrackMetadataResponse,
    )
    params = RequestParameters(
        page=page, genome_build=genome_build, filter=filter, keyword=keyword
    )
    service = FILEREndpointService(internal, response_config, params)
    return await service.search_track_metadata()


@router.get(
    "/tracks/data",
    response_model=Union[BEDResponse, DataResponse],
    summary="search-track-data",
    description=(
        "Retrieve FILER track data by region, optionally constrained by "
        "structured track metadata filters."
    ),
)
async def search_track_data(
    filter=Depends(TEXT_FILTER_PARAMETER),
    keyword: str = Depends(keyword_param),
    genome_build: str = Depends(assembly_param),
    span: str = Depends(span_param),
    page: int = Depends(page_param),
    content: str = Query(
        ResponseContent.FULL,
        description=ResponseContent.feature_record().description(),
    ),
    format: str = Query(
        ResponseFormat.JSON,
        description=DefaultResponseFormatParam.description(),
    ),
    internal: FILEREndpointRequestParameters = Depends(),
) -> Union[BEDResponse, DataResponse]:
    if filter is None and keyword is None:
        raise ValidationError(
            "must specify either a `filter` and/or a `keyword` to search"
        )

    response_content = ResponseContent.feature_record().validate(content)
    response_config = ResponseConfiguration(
        format=ResponseFormat.validate(format),
        content=response_content,
        model=(
            BEDResponse if response_content == ResponseContent.FULL else DataResponse
        ),
    )
    params = RequestParameters(
        page=page,
        genome_build=genome_build,
        span=span,
        filter=filter,
        keyword=keyword,
    )
    service = FILEREndpointService(internal, response_config, params)
    return await service.search_track_data()
