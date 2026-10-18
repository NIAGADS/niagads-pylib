"""Variant record endpoints for the NIAGADS Open Access API."""

from typing import Union

from fastapi import APIRouter, Depends, Path, Query
from niagads.api.common.models.context.request import Parameters
from niagads.api.common.models.context.response import ResponseConfiguration
from niagads.api.common.models.entities.variant.records import Variant, VariantBrief
from niagads.api.common.models.responses.records import (
    RecordMappingResponse,
    RecordResponse,
)
from niagads.api.common.parameters.response.pagination import page_param
from niagads.api.common.parameters.response.response import (
    record_response_content_param,
    record_response_format_param,
)
from niagads.api.common.parameters.validators import parse_comma_separated_list
from niagads.api.common.services.variant import VariantEndpointService
from niagads.api.common.types import ResponseContent, ResponseFormat
from niagads.api.common.utils import sanitize
from niagads.common.genomic.features.models import GenomicFeature
from niagads.common.genomic.features.types import GenomicFeatureType
from niagads.open_access_api.dependencies import OpenAccessEndpointContext

router = APIRouter(prefix="/record/variant", tags=["Variant"])


# -------------------------------------------
# Record-specific parameters
# -------------------------------------------
async def path_variant_id(
    variant: str = Path(
        title="Variant identifier",
        description=(
            "Variant record identifier: RefSNP ID, structural variant ID, "
            "or positional allelic identifier"
        ),
        examples=["rs7412", "1:44908822:C:T", "DUP_CHR1_4AE4CDB8"],
    ),
) -> str:
    return GenomicFeature(
        feature_id=sanitize(variant), feature_type=GenomicFeatureType.VARIANT
    ).feature_id


async def query_variant_ids(
    ids: str = Query(
        title="Variant identifiers",
        description="A comma-separated list of variant record identifiers",
        examples=["rs7412,1:44908822:C:T"],
    ),
) -> list[str]:
    return [
        GenomicFeature(
            feature_id=sanitize(variant), feature_type=GenomicFeatureType.VARIANT
        ).feature_id
        for variant in parse_comma_separated_list(ids)
    ]


# -------------------------------------------
# Routes
# -------------------------------------------
@router.get(
    "/",
    summary="Get variant records",
    description="Retrieve variant records for the specified identifiers.",
    response_description="Variant records.",
    operation_id="getVariants",
    response_model=Union[
        RecordMappingResponse[Variant], RecordMappingResponse[VariantBrief]
    ],
)
async def get_variants(
    ids: list[str] = Depends(query_variant_ids),
    context: OpenAccessEndpointContext = Depends(),
    format: ResponseFormat = Depends(record_response_format_param),
    content: ResponseContent = Depends(record_response_content_param),
    page: int = Depends(page_param),
) -> RecordMappingResponse:
    record_model = VariantBrief if content == ResponseContent.SUMMARY else Variant
    service = VariantEndpointService(
        context=context,
        parameters=Parameters(variants=ids, page=page),
        response_config=ResponseConfiguration(
            format=format,
            content=content,
            response_model=RecordMappingResponse,
            record_model=record_model,
        ),
    )

    result = await service.get_record_mappings(ids)
    return await service.generate_response(result)


@router.get(
    "/{variant}",
    summary="Get variant record",
    description="Retrieve the variant record for the specified identifier.",
    response_description="Variant record.",
    operation_id="getVariant",
    response_model=RecordResponse,
)
async def get_variant(
    variant: str = Depends(path_variant_id),
    context: OpenAccessEndpointContext = Depends(),
    format: ResponseFormat = Depends(record_response_format_param),
    content: ResponseContent = Depends(record_response_content_param),
) -> RecordResponse:
    record_model = VariantBrief if content == ResponseContent.SUMMARY else Variant
    service = VariantEndpointService(
        context=context,
        parameters=Parameters(variant=variant),
        response_config=ResponseConfiguration(
            format=format,
            content=content,
            response_model=RecordMappingResponse,
            record_model=record_model,
        ),
    )

    result = await service.fetch_record(variant)
    return await service.generate_response(result, is_paged=True)
