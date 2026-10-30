"""Track record endpoints for the NIAGADS Open Access API."""

from typing import Union

from fastapi import APIRouter, Depends, Path, Query
from niagads.api.common.models.annotations.associations import VariantAssociation
from niagads.api.common.models.context.request import Parameters
from niagads.api.common.models.context.response import ResponseConfiguration
from niagads.api.common.models.entities.track.records import (
    TrackMetadata,
    TrackMetadataBrief,
)
from niagads.api.common.models.records.types import DynamicRecord
from niagads.api.common.models.responses.records import (
    RecordMappingResponse,
    RecordResponse,
)
from niagads.api.common.parameters.location import location_param
from niagads.api.common.parameters.response.pagination import page_param
from niagads.api.common.parameters.response.response import (
    data_response_content_param,
    record_response_content_param,
    record_response_format_param,
    response_format_param,
)
from niagads.api.common.parameters.validators import parse_comma_separated_list
from niagads.api.common.services.gene import GeneEndpointService
from niagads.api.common.services.region import RegionEndpointService
from niagads.api.common.services.track import TrackEndpointService
from niagads.api.common.services.variant import VariantEndpointService
from niagads.api.common.types import ResponseContent, ResponseFormat
from niagads.api.common.utils import sanitize
from niagads.common.genomic.features.models import GenomicFeature
from niagads.common.genomic.features.types import GenomicFeatureType
from niagads.open_access_api.dependencies import OpenAccessEndpointContext

router = APIRouter(prefix="/record/track", tags=["Track"])


# -------------------------------------------
# Record-specific parameters
# -------------------------------------------
async def path_track_id(
    track: str = Path(
        title="Track identifier",
        description="Stable track identifier.",
    ),
) -> str:
    return sanitize(track)


async def query_track_ids(
    ids: str = Query(
        title="Track identifiers",
        description="A comma-separated list of stable track identifiers.",
    ),
) -> list[str]:
    return [sanitize(track) for track in parse_comma_separated_list(ids)]


# -------------------------------------------
# Routes
# -------------------------------------------
@router.get(
    "/",
    summary="Get track records",
    description="Retrieve the canonical records for the specified tracks.",
    response_description="Track records.",
    operation_id="getTracks",
    response_model=Union[
        RecordMappingResponse[TrackMetadata],
        RecordMappingResponse[TrackMetadataBrief],
    ],
)
async def get_tracks(
    ids: list[str] = Depends(query_track_ids),
    context: OpenAccessEndpointContext = Depends(),
    format: ResponseFormat = Depends(record_response_format_param),
    content: ResponseContent = Depends(record_response_content_param),
    page: int = Depends(page_param),
) -> RecordMappingResponse:
    record_model = (
        TrackMetadataBrief if content == ResponseContent.SUMMARY else TrackMetadata
    )
    service = TrackEndpointService(
        context=context,
        parameters=Parameters(tracks=ids, page=page),
        response_config=ResponseConfiguration(
            format=format,
            content=content,
            response_model=RecordMappingResponse,
            record_model=record_model,
        ),
    )

    result = await service.get_cached_response()
    from_cache = True
    if not result:
        result = await service.get_record_mappings(ids)
        from_cache = False
    response = await service.generate_response(result, from_cache=from_cache)
    return response


@router.get(
    "/{track}",
    summary="Get track record",
    description="Retrieve the canonical record for the specified track.",
    response_description="Track record.",
    operation_id="getTrack",
    response_model=Union[
        RecordResponse[TrackMetadata], RecordResponse[TrackMetadataBrief]
    ],
)
async def get_track(
    track: str = Depends(path_track_id),
    context: OpenAccessEndpointContext = Depends(),
    format: ResponseFormat = Depends(record_response_format_param),
    content: ResponseContent = Depends(record_response_content_param),
) -> RecordResponse:
    record_model = (
        TrackMetadataBrief if content == ResponseContent.SUMMARY else TrackMetadata
    )
    service = TrackEndpointService(
        context=context,
        parameters=Parameters(track=track),
        response_config=ResponseConfiguration(
            format=format,
            content=content,
            response_model=RecordResponse,
            record_model=record_model,
        ),
    )

    result = await service.get_cached_response()
    from_cache = True
    if not result:
        result = await service.fetch_record(track)
        from_cache = False
    response = await service.generate_response(result, from_cache=from_cache)
    return response


@router.get(
    "/{track}/data",
    summary="Get track data",
    description=(
        "Retrieve variant associations for the specified track with a region, "
        "specified as a gene identifier, variant identifier, or genomic span."
    ),
    response_description="Track variation associations.",
    operation_id="getTrackData",
    response_model=Union[
        RecordResponse[VariantAssociation], RecordResponse[DynamicRecord]
    ],
)
async def get_track_data(
    track: str = Depends(path_track_id),
    location: GenomicFeature = Depends(location_param),
    context: OpenAccessEndpointContext = Depends(),
    format: ResponseFormat = Depends(response_format_param),
    content: ResponseContent = Depends(data_response_content_param),
    page: int = Depends(page_param),
) -> RecordResponse:
    summary = content == ResponseContent.SUMMARY
    record_model = DynamicRecord if summary else VariantAssociation
    parameters = Parameters(track=track, loc=location.feature_id, page=page)

    service = TrackEndpointService(
        context=context,
        parameters=parameters,
        response_config=ResponseConfiguration(
            format=format,
            content=content,
            response_model=RecordResponse,
            record_model=record_model,
        ),
    )

    result = await service.get_cached_response()
    from_cache = True
    if not result:
        location_service_class = {
            GenomicFeatureType.GENE: GeneEndpointService,
            GenomicFeatureType.VARIANT: VariantEndpointService,
            GenomicFeatureType.REGION: RegionEndpointService,
        }[location.feature_type]
        location_service = location_service_class(
            context=context,
            parameters=parameters,
            response_config=None,
        )
        region = await location_service.get_feature_location(location.feature_id)
        result = await service.fetch_associations(track, region=region, summary=summary)
        from_cache = False
    response = await service.generate_response(result, from_cache=from_cache)
    return response
