import functools

from fastapi import APIRouter, Request, Response
from niagads.open_access_api_common.app import AppFactory
from niagads.open_access_api_common.config.constants import SharedOpenAPITags

router = APIRouter()


@router.get(
    "/",
    tags=[str(SharedOpenAPITags.ABOUT)],
)
async def about_niagads_open_access_api():
    """About the service"""
    return {"messge": "NIAGADS Open Access API"}


@router.get(
    "/openapi.yaml",
    tags=[str(SharedOpenAPITags.SPECIFICATION)],
    name="Specification: `YAML`",
    description="Get API Specificiation in `YAML` format",
    # include_in_schema=False,
)
@functools.lru_cache()
def read_openapi_yaml(request: Request) -> Response:
    return Response(AppFactory.get_openapi_yaml(request.app), media_type="text/yaml")
