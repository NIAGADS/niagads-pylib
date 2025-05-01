import yaml
import traceback
import functools

from io import StringIO
from fastapi import FastAPI, Request, status
from fastapi.responses import JSONResponse, Response
from fastapi.exceptions import RequestValidationError
from fastapi.encoders import jsonable_encoder
from fastapi.middleware.cors import CORSMiddleware

# from starlette.middleware.cors import CORSMiddleware

# from starlette.middleware.sessions import SessionMiddleware
from asgi_correlation_id import CorrelationIdMiddleware

from api.config.metadata import ROUTE_TAGS
from api.config.settings import Settings
from .routes import FILERRouter, GenomicsRouter

# FIXME -- needed for applications reading the openapi.json or openapi.yaml, but
# needs to be dynamic based on deployment
# SERVER = {'url' :"http://localhost:8000/api"}


app = FastAPI(
    title="NIAGADS Open Access - API",
    description="an application programming interface (API) that provides programmatic access to Open-Access resources at the NIA Genetics of Alzheimer's Disease Data Storage Site (NIAGADS)",
    summary="NIAGADS API",
    version="0.9.5b",  # FIXME: get from settings
    terms_of_service="http://example.com/terms/",
    contact={"name": "NIAGADS Support", "email": Settings.from_env().ADMIN_EMAIL},
    license_info={
        "name": "Apache 2.0",
        "url": "https://www.apache.org/licenses/LICENSE-2.0.html",
    },
    # servers=[{"url": Settings.from_env().API_PUBLIC_URL}]
    # root_path="/api",
    swagger_ui_parameters={
        "apisSorter": "alpha",
        "operationsSorter": "alpha",
        "tagsSorter": "alpha",
    },
    openapi_tags=ROUTE_TAGS,
)

# app.add_middleware(SessionMiddleware, secret_key=Settings.from_env().SESSION_SECRET)
app.add_middleware(CorrelationIdMiddleware, header_name="X-Request-ID")
app.add_middleware(
    CORSMiddleware,
    # allow_origins=[Settings.from_env().API_PUBLIC_URL],
    allow_origins=["*"],
    allow_origin_regex=r"https://.*\.niagads\.org",
    # allow_credentials=False,
    allow_methods=["GET"],
    allow_headers=["*"],
)


app.include_router(FILERRouter)
app.include_router(GenomicsRouter)


@app.get("/", include_in_schema=False)
async def read_root():
    return {"messge": "NIAGADS API Route"}


# get yaml version of openapi.json
# from https://github.com/tiangolo/fastapi/issues/1140#issuecomment-659469034


@app.get(
    "/openapi.yaml",
    tags=["OpenAPI Specification"],
    name="YAML",
    description="Get openapi.yaml",
)
@functools.lru_cache()
def read_openapi_yaml() -> Response:
    openapi_json = app.openapi()
    yaml_s = StringIO()
    yaml.dump(openapi_json, yaml_s)
    return Response(yaml_s.getvalue(), media_type="text/yaml")
