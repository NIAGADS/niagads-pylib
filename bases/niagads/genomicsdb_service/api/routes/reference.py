from fastapi import APIRouter

router = APIRouter(prefix="/reference", tags=["Reference"])


@router.get(
    "/filters",
    summary="get-filter-fields",
    description="List available GenomicsDB structured search filter fields.",
)
async def get_filters():
    pass


@router.get(
    "/filters/{field}",
    summary="get-filter-values",
    description="List available values for a GenomicsDB structured search filter field.",
)
async def get_filter_values(field: str):
    pass


@router.get(
    "/assemblies",
    summary="get-genome-assemblies",
    description="List genome assemblies supported by GenomicsDB endpoints.",
)
async def get_assemblies():
    pass


@router.get(
    "/formats",
    summary="get-response-formats",
    description="List response formats supported by GenomicsDB endpoints.",
)
async def get_formats():
    pass


@router.get(
    "/content",
    summary="get-response-content-options",
    description="List response content options supported by GenomicsDB endpoints.",
)
async def get_content():
    pass


@router.get(
    "/views",
    summary="get-response-views",
    description="List response views supported by GenomicsDB endpoints.",
)
async def get_views():
    pass
