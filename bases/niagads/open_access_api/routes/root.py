import functools

from fastapi import APIRouter, Request, Response
from niagads.open_access_api_common.app.factory import AppFactory
from niagads.open_access_api_common.config.constants import SharedOpenAPITags

router = APIRouter()


@router.get(
    "/",
    summary="get-api-info",
    tags=[str(SharedOpenAPITags.DOCUMENTATION)],
)
async def about_niagads_open_access_api():
    """Retrieve a brief overview of the NIAGADS Open Access Resources."""
    return {
        "messge": "You've reached the NIAGADS Open Access API; please visit https://api.niagads.org/docs for more information"
    }


@router.get(
    "/openapi.yaml",
    tags=[str(SharedOpenAPITags.DOCUMENTATION)],
    summary="get-specification-yaml",
    description="Retrieve the full NIAGADS Open Access API Specificiation in `YAML` format",
    # include_in_schema=False,
)
@functools.lru_cache()
def read_openapi_yaml(request: Request) -> Response:
    return Response(AppFactory.get_openapi_yaml(request.app), media_type="text/yaml")
