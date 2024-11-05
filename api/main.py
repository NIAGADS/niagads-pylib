import yaml
import traceback
import functools

from io import StringIO
from fastapi import FastAPI, Request, status
from fastapi.responses import JSONResponse, Response
from fastapi.openapi.models import Server
from fastapi.exceptions import RequestValidationError
from fastapi.encoders import jsonable_encoder
from fastapi.middleware.cors import CORSMiddleware

# from starlette.middleware.sessions import SessionMiddleware
from asgi_correlation_id import CorrelationIdMiddleware

from api.internal.config import get_settings
from .routers import FILERRouter, RedirectRouter

# FIXME -- needed for applications reading the openapi.json or openapi.yaml, but 
# needs to be dynamic based on deployment
# SERVER = {'url' :"http://localhost:8000/api"}

app = FastAPI(
        title="NIAGADS Open Access - API",
        description="an application programming interface (API) that provides programmatic access to Open-Access resources at the NIA Genetics of Alzheimer's Disease Data Storage Site (NIAGADS)",
        summary="NIAGADS API",
        version="0.9.0a", # FIXME: get from settings
        terms_of_service="http://example.com/terms/",
        contact={
            "name": "NIAGADS Support",
            "email": "help@niagads.org",
        },
        license_info={
            "name": "Apache 2.0",
            "url": "https://www.apache.org/licenses/LICENSE-2.0.html",
        },
        # servers=[{"url": get_settings().API_PUBLIC_URL}]
        # root_path="/api",
        #swagger_ui_parameters={"docExpansion": "full"}
    )

# app.add_middleware(SessionMiddleware, secret_key=get_settings().SESSION_SECRET)
app.add_middleware(CorrelationIdMiddleware, header_name="X-Request-ID")
app.add_middleware(CORSMiddleware, 
    allow_origins=[get_settings().API_PUBLIC_URL],
    # allow_credentials=True
    allow_methods=['*'],
    allow_headers=['*'])

@app.exception_handler(RuntimeError)
async def validation_exception_handler(request: Request, exc: RuntimeError):
    query = request.url.path 
    if request.url.query != '':
        query += '?' + request.url.query
    return JSONResponse(
        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        content=jsonable_encoder(
            {
                "error": str(exc),  # optionally, include the pydantic errors
                "msg": "An unexpected error occurred.  Please submit a `bug` GitHub issue containing this full error response at: https://github.com/NIAGADS/niagads-api/issues",
                "stack_trace": [ t.replace('\n', '').replace('"', "'") for t in traceback.format_tb(exc.__traceback__) ],
                "request": str(query)
            }), 
    )
    
@app.exception_handler(NotImplementedError)
async def validation_exception_handler(request: Request, exc: NotImplementedError):
    return JSONResponse(
        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        content=jsonable_encoder(
            {
                "error": str(exc), 
                "msg": "Not yet implemented"
            }), 
    )

@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError):
    return JSONResponse(
        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        content=jsonable_encoder(
            {
                "error": str(exc), 
                "msg": "Invalid parameter value"
            }), 
    )



# TODO: what is this handling? -- remove?
@app.exception_handler(OSError)
async def validation_exception_handler(request: Request, exc: OSError):
    query = request.url.path 
    if request.url.query != '':
        query += '?' + request.url.query
    return JSONResponse(
        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        content=jsonable_encoder(
            {
                "message": str(exc),  # optionally, include the pydantic errors
                "error": "An system error occurred.  Please email this error response to `help@niagads.org` with the subject 'NIAGADS API Systems Error' and we will try and resolve the isse as soon as possible.",
                "stack_trace": [ t.replace('\n', '').replace('"', "'") for t in traceback.format_tb(exc.__traceback__) ],
                "request": str(query)
            }), 
    )

app.include_router(FILERRouter)
app.include_router(RedirectRouter)


@app.get("/", include_in_schema=False)
async def read_root():
    return {"messge": "NIAGADS API Route"}

# get yaml version of openapi.json
# from https://github.com/tiangolo/fastapi/issues/1140#issuecomment-659469034

@app.get('/openapi.yaml', tags=["OpenAPI Specification"], name="YAML", description="Get openapi.yaml")
@functools.lru_cache()
def read_openapi_yaml() -> Response:
    openapi_json= app.openapi()
    yaml_s = StringIO()
    yaml.dump(openapi_json, yaml_s)
    return Response(yaml_s.getvalue(), media_type='text/yaml')

