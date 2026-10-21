"""Region endpoint contracts awaiting local ORM retrieval integration."""

from typing import Union

from fastapi import APIRouter, Depends, HTTPException, Query
from niagads.api.common.models.annotations.associations import VariantAssociation
from niagads.api.common.models.records.types import DynamicRecord
from niagads.api.common.models.responses.records import RecordResponse
from niagads.api.common.parameters.response.pagination import page_param
from niagads.api.common.parameters.response.response import (
    data_response_content_param,
    response_format_param,
)
from niagads.api.common.types import ResponseContent, ResponseFormat
from niagads.common.genomic.regions.models import OneBasedGenomicRegion
from niagads.exceptions.core import ValidationError as NiagadsValidationError
from niagads.genome_reference.human import HumanGenome

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
    description=(
        "Retrieve associations in a one-based inclusive region. "
        "ORM retrieval integration is pending. Valid requests currently return 501."
    ),
    response_description="Regional association records or per-track summaries.",
    operation_id="getRegionAssociations",
    openapi_extra={"x-status": "planned"},
    response_model=Union[
        RecordResponse[VariantAssociation], RecordResponse[DynamicRecord]
    ],
    responses={501: {"description": "ORM retrieval integration is pending"}},
)
async def get_region_associations(
    region: OneBasedGenomicRegion = Depends(query_region),
    format: ResponseFormat = Depends(response_format_param),
    content: ResponseContent = Depends(data_response_content_param),
    page: int = Depends(page_param),
) -> RecordResponse:
    """Declare the future region API without accessing the database."""
    raise NotImplementedError(
        "Region associations require ORM retrieval integration; "
        "this prototype does not execute database queries."
    )
