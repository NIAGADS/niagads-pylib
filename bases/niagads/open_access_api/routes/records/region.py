"""Regional association and variant record retrieval."""

from typing import Union

from fastapi import APIRouter, Depends
from niagads.api.common.models.annotations.associations import VariantAssociation
from niagads.api.common.models.context.request import Parameters
from niagads.api.common.models.context.response import ResponseConfiguration
from niagads.api.common.models.entities.variant.records import Variant, VariantBrief
from niagads.api.common.models.records.types import DynamicRecord
from niagads.api.common.models.responses.records import RecordResponse
from niagads.api.common.parameters.identifiers import region_id
from niagads.api.common.parameters.response.pagination import page_param
from niagads.api.common.parameters.response.response import (
    data_response_content_param,
    response_format_param,
)
from niagads.api.common.services.region import RegionEndpointService
from niagads.api.common.types import ResponseContent, ResponseFormat
from niagads.common.genomic.features.models import GenomicFeature
from niagads.open_access_api.dependencies import OpenAccessEndpointContext

REGION_VARIANT_LIMIT = 5_000

router = APIRouter(prefix="/record/region", tags=["Region"])


@router.get(
    "/{region}/associations",
    summary="Get region associations",
    description="Retrieve associations in a genomic span.",
    response_description="Regional association records or per-track summaries.",
    operation_id="getRegionAssociations",
    response_model=Union[
        RecordResponse[VariantAssociation], RecordResponse[DynamicRecord]
    ],
)
async def get_region_associations(
    region: GenomicFeature = Depends(region_id),
    context: OpenAccessEndpointContext = Depends(),
    format: ResponseFormat = Depends(response_format_param),
    content: ResponseContent = Depends(data_response_content_param),
    page: int = Depends(page_param),
) -> RecordResponse:
    summary = content == ResponseContent.SUMMARY
    service = RegionEndpointService(
        context=context,
        parameters=Parameters(region=region.feature_id, page=page),
        response_config=ResponseConfiguration(
            format=format,
            content=content,
            response_model=RecordResponse,
            record_model=DynamicRecord if summary else VariantAssociation,
        ),
    )

    result = await service.get_cached_response()
    from_cache = True
    if not result:
        result = await service.fetch_associations(region.feature_id, summary=summary)
        from_cache = False

    return await service.generate_response(result, from_cache=from_cache)


@router.get(
    "/{region}/variants",
    summary="Get region variants",
    description=(
        "Retrieve up to 5,000 variants ordered by position in a genomic span "
        "of less than 100,000 bp. Query smaller windows to fetch the whole region."
    ),
    response_description="Regional variant records.",
    operation_id="getRegionVariants",
    response_model=Union[RecordResponse[Variant], RecordResponse[VariantBrief]],
)
async def get_region_variants(
    region: GenomicFeature = Depends(region_id),
    context: OpenAccessEndpointContext = Depends(),
    format: ResponseFormat = Depends(response_format_param),
    content: ResponseContent = Depends(data_response_content_param),
    page: int = Depends(page_param),
) -> RecordResponse:
    service = RegionEndpointService(
        context=context,
        parameters=Parameters(region=region.feature_id, page=page),
        response_config=ResponseConfiguration(
            format=format,
            content=content,
            response_model=RecordResponse,
            record_model=(
                VariantBrief if content == ResponseContent.SUMMARY else Variant
            ),
        ),
    )

    message = None
    result = await service.get_cached_response()
    from_cache = True
    if not result:
        count = await service.fetch_variants(region.feature_id, counts_only=True)
        result = await service.fetch_variants(
            region.feature_id, limit=REGION_VARIANT_LIMIT
        )
        if count > REGION_VARIANT_LIMIT:
            message = [
                f"{count:,} variants found in region, returning first "
                f"{REGION_VARIANT_LIMIT:,}. Please run windowed queries to "
                "fetch across the whole region."
            ]
        from_cache = False

    return await service.generate_response(
        result, from_cache=from_cache, message=message
    )
