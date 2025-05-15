import functools

from fastapi import APIRouter, Request, Response
from niagads.open_access_api_common.utils import get_openapi_yaml

router = APIRouter()


@router.get("/", include_in_schema=False)
async def read_root():
    """About the service"""
    return {"messge": "NIAGADS Open Access API"}



@router.get(
    "/openapi.yaml",
    tags=["OpenAPI Specification"],
    name="Specification: `YAML`",
    description="Get API Specificiation in `YAML` format",
)
@functools.lru_cache()
def read_openapi_yaml(request: Request) -> Response:
    return get_openapi_yaml(request)