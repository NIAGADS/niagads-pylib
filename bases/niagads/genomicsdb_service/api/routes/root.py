from fastapi import APIRouter

router = APIRouter(tags=["Status"])


@router.get(
    "/status",
    summary="get-api-status",
    description="Retrieve basic GenomicsDB API status and service information.",
)
async def get_status():
    pass


@router.get(
    "/openapi.yaml",
    summary="get-openapi-yaml",
    description="Retrieve the GenomicsDB OpenAPI specification in YAML format.",
)
async def get_openapi_yaml():
    pass
