import functools

from fastapi import APIRouter, Request, Response
from niagads.open_access_api_common.app import AppFactory

router = APIRouter()


@router.get(
    "/",
    include_in_schema=False,
    tags=["Service Information"],
)
async def about_niagads_open_access_api():
    """About the service"""
    return {"messge": "NIAGADS Open Access API"}


@router.get(
    "/openapi.yaml",
    tags=["OpenAPI Specification"],
    name="Specification: `YAML`",
    description="Get API Specificiation in `YAML` format",
    include_in_schema=False,
)
@functools.lru_cache()
def read_openapi_yaml(request: Request) -> Response:
    return Response(AppFactory.get_openapi_yaml(request.app), media_type="text/yaml")
