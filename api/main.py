import functools
import yaml

from io import StringIO
from fastapi import FastAPI, Request, status
from fastapi.responses import JSONResponse, Response
from fastapi.encoders import jsonable_encoder
from fastapi.openapi.models import Server

from .routers import filer

# FIXME -- needed for applications reading the openapi.json or openapi.yaml, but 
# needs to be dynamic based on deployment
SERVER = {'url' :"http://localhost:8000/api"}

app = FastAPI(
        title="NIAGADS API",
        description="an application programming interface (API) that provides programmatic access to Open-Access resources at the NIA Genetics of Alzheimer's Disease Data Storage Site (NIAGADS)",
        summary="NIAGADS API",
        version="0.0.1",
        terms_of_service="http://example.com/terms/",
        contact={
            "name": "NIAGADS Support",
            "email": "help@niagads.org",
        },
        license_info={
            "name": "Apache 2.0",
            "url": "https://www.apache.org/licenses/LICENSE-2.0.html",
        },
        root_path="/api",
        servers=[SERVER],
        #swagger_ui_parameters={"docExpansion": "full"}
    )


@app.exception_handler(ValueError)
async def validation_exception_handler(request: Request, exc: ValueError):
    return JSONResponse(
        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        content=jsonable_encoder(
            {
                "message": str(exc),  # optionally, include the pydantic errors
                "error": "Invalid parameter value"
            }), 
    )

@app.exception_handler(LookupError)
async def validation_exception_handler(request: Request, exc: ValueError):
    return JSONResponse(
        status_code=status.HTTP_400_BAD_REQUEST,
        content=jsonable_encoder(
            {
                "message": str(exc),  # optionally, include the pydantic errors
                 "error": "Invalid external request"
            }),
    )


app.include_router(filer)


@app.get("/")
async def read_root():
    return {"messge": "NIAGADS API Route"}

# get yaml version of openapi.json
# from https://github.com/tiangolo/fastapi/issues/1140#issuecomment-659469034
@app.get('/openapi.yaml', include_in_schema=False)
@functools.lru_cache()
def read_openapi_yaml() -> Response:
    openapi_json= app.openapi()
    yaml_s = StringIO()
    yaml.dump(openapi_json, yaml_s)
    return Response(yaml_s.getvalue(), media_type='text/yaml')

