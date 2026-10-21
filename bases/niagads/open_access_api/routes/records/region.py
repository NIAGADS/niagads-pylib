"""Regional association retrieval and planned variant retrieval."""

from typing import Union

from fastapi import APIRouter, Depends, HTTPException, Query
from niagads.api.common.models.annotations.associations import VariantAssociation
from niagads.api.common.models.context.request import Parameters
from niagads.api.common.models.context.response import ResponseConfiguration
from niagads.api.common.models.entities.variant.records import Variant, VariantBrief
from niagads.api.common.models.records.types import DynamicRecord
from niagads.api.common.models.responses.records import RecordResponse
from niagads.api.common.parameters.response.pagination import page_param
from niagads.api.common.parameters.response.response import (
    data_response_content_param,
    response_format_param,
)
from niagads.api.common.services.region import RegionEndpointService
from niagads.api.common.types import ResponseContent, ResponseFormat
from niagads.common.genomic.regions.models import OneBasedGenomicRegion
from niagads.exceptions.core import ValidationError as NiagadsValidationError
from niagads.genome_reference.human import HumanGenome
from niagads.open_access_api.dependencies import OpenAccessEndpointContext

router = APIRouter(prefix="/record/region", tags=["Region"])


async def query_region(
    region: str | None = Query(default=None, examples=["chr19:100-200"]),
    chr: HumanGenome | None = Query(default=None, description="Chromosome"),
    start: int | None = Query(default=None, gt=0),
    end: int | None = Query(default=None, gt=0),
) -> OneBasedGenomicRegion:
    """Validate one-based inclusive coordinates supplied in exactly one form."""
    coordinates = (chr, start, end)
    if region is not None and any(value is not None for value in coordinates):
        raise HTTPException(422, "Use region or chr/start/end, not both")
    try:
        if region is not None:
            parsed = OneBasedGenomicRegion.from_region_id(region)
        elif all(value is not None for value in coordinates):
            parsed = OneBasedGenomicRegion(chromosome=chr, start=start, end=end)
        else:
            raise ValueError("Supply region or all of chr/start/end")
        if parsed.start < 1 or parsed.end < parsed.start:
            raise ValueError("Coordinates must be positive with start <= end")
        return parsed
    except (ValueError, IndexError, TypeError, NiagadsValidationError) as exc:
        raise HTTPException(422, "Invalid one-based inclusive genomic region") from exc


@router.get(
    "/associations",
    summary="Get region associations",
    description="Retrieve associations in a one-based inclusive region.",
    response_description="Regional association records or per-track summaries.",
    operation_id="getRegionAssociations",
    response_model=Union[
        RecordResponse[VariantAssociation], RecordResponse[DynamicRecord]
    ],
)
async def get_region_associations(
    region: OneBasedGenomicRegion = Depends(query_region),
    context: OpenAccessEndpointContext = Depends(),
    format: ResponseFormat = Depends(response_format_param),
    content: ResponseContent = Depends(data_response_content_param),
    page: int = Depends(page_param),
) -> RecordResponse:
    summary = content == ResponseContent.SUMMARY
    service = RegionEndpointService(
        context=context,
        parameters=Parameters(region=str(region), page=page),
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
        result = await service.fetch_associations(str(region), summary=summary)
        from_cache = False

    return await service.generate_response(result, from_cache=from_cache)


@router.get(
    "/variants",
    summary="Get region variants",
    description=(
        "Retrieve all variants in a one-based inclusive region, with pagination. "
        "ORM retrieval integration is pending. Valid requests currently return 501."
    ),
    response_description="Regional variant records.",
    operation_id="getRegionVariants",
    openapi_extra={"x-status": "planned"},
    response_model=Union[RecordResponse[Variant], RecordResponse[VariantBrief]],
    responses={501: {"description": "ORM retrieval integration is pending"}},
)
async def get_region_variants(
    region: OneBasedGenomicRegion = Depends(query_region),
    format: ResponseFormat = Depends(response_format_param),
    content: ResponseContent = Depends(data_response_content_param),
    page: int = Depends(page_param),
) -> RecordResponse:
    """Declare regional variant retrieval pending ORM integration."""
    raise NotImplementedError("Region variants require ORM retrieval integration.")
