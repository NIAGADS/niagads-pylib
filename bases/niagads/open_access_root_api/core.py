from niagads.open_access_api_exception_handlers.core import (
    add_not_implemented_exception_handler,
    add_runtime_exception_handler,
    add_system_exception_handler,
    add_validation_exception_handler,
)
import yaml
import traceback
import functools

from io import StringIO
from fastapi import FastAPI, Response
from fastapi.middleware.cors import CORSMiddleware

# TODO, generate at build from other services
# see https://fastapi.tiangolo.com/how-to/custom-docs-ui-assets/#disable-the-automatic-docs

app = FastAPI(
    title="NIAGADS Open Access API",
    description="an application programming interface (API) that provides programmatic access to Open Access resources at the NIA Genetics of Alzheimer's Disease Data Storage Site (NIAGADS)",
    summary="NIAGADS Open Access API",
    version="0.0.1",  # FIXME: get from settings
    # terms_of_service="http://example.com/terms/",
    # contact={"name": "NIAGADS Support", "email": get_settings().ADMIN_EMAIL},
    license_info={
        "name": "Apache 2.0",
        "url": "https://www.apache.org/licenses/LICENSE-2.0.html",
    },
    # servers=[{"url": get_settings().API_PUBLIC_URL}],
    swagger_ui_parameters={
        "apisSorter": "alpha",
        "operationsSorter": "alpha",
        "tagsSorter": "alpha",
    },
    docs_url=None,
    redoc_url=None,
    # default_response_class=BaseResponseModel,
    # openapi_tags=ROUTE_TAGS,
)


# TODO make CORS conditional on production v dev
app.add_middleware(
    CORSMiddleware,
    # allow_origins=[get_settings().API_PUBLIC_URL],
    allow_origins=["*"],
    allow_origin_regex=r"https://.*\.niagads\.org",
    # allow_credentials=False,
    allow_methods=["GET"],
    allow_headers=["*"],
)


add_runtime_exception_handler(app)
add_validation_exception_handler(app)
add_system_exception_handler(app)
add_not_implemented_exception_handler(app)


@app.get("/", include_in_schema=False)
async def read_root():
    """About the service"""
    return {"messge": "NIAGADS API Route"}


@app.get(
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
    openapi_json = app.openapi()
    yaml_s = StringIO()
    yaml.dump(openapi_json, yaml_s)
    return Response(yaml_s.getvalue(), media_type="text/yaml")
