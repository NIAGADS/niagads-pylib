import functools
from io import StringIO
from fastapi import APIRouter, Response
import yaml


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
def read_openapi_yaml() -> Response:
    """Get YAML-formatted openapi specification.

    Converts the API openapi JSON specification to yaml format and returns the formatted yaml

    adapted from https://github.com/tiangolo/fastapi/issues/1140#issuecomment-659469034
    """
    openapi_json = router.app.openapi()
    yaml_s = StringIO()
    yaml.dump(openapi_json, yaml_s)
    return Response(yaml_s.getvalue(), media_type="text/yaml")
