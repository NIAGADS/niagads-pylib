"""JSON service endpoints for external applications."""

from re import IGNORECASE

from fastapi import APIRouter, Depends, Query
from niagads.api.common.models.context.request import Parameters
from niagads.api.common.parameters.location import flank_param
from niagads.api.common.services.gene import GeneEndpointService
from niagads.api.common.services.variant import VariantEndpointService
from niagads.open_access_api.dependencies import OpenAccessEndpointContext
from niagads.utils.regular_expressions import RegularExpressions
from niagads.utils.string import matches

router = APIRouter(prefix="/service", tags=["Service"])


@router.get(
    "/feature",
    summary="Get feature location",
    description="Resolve a gene or variant identifier to one-based coordinates.",
    operation_id="getFeatureLocation",
)
async def get_feature_location(
    id: str = Query(
        description=(
            "Gene symbol, Ensembl gene ID, positional variant ID, "
            "NIAGADS structural variant ID, or RefSNP ID."
        )
    ),
    flank: int = Depends(flank_param),
    context: OpenAccessEndpointContext = Depends(),
) -> dict[str, str | int]:
    is_variant = any(
        matches(pattern, id, flags=IGNORECASE)
        for pattern in (
            RegularExpressions.POSITIONAL_VARIANT_ID,
            RegularExpressions.STRUCTUAL_VARIANT_ID,
            RegularExpressions.REF_SNP_ID,
        )
    )
    service_class = VariantEndpointService if is_variant else GeneEndpointService
    service = service_class(
        context=context,
        parameters=Parameters(id=id, flank=flank),
        response_config=None,
    )
    location = await service.get_feature_location(id, flank=flank)
    return {
        "chr": str(location.chromosome),
        "start": location.start,
        "end": location.end,
    }
