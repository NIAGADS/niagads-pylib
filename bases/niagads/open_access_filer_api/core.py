from asgi_correlation_id import CorrelationIdMiddleware
from fastapi import APIRouter, FastAPI

from niagads.open_access_api_common.exception_handlers import (
    add_not_implemented_exception_handler,
    add_runtime_exception_handler,
    add_system_exception_handler,
    add_validation_exception_handler,
)
from niagads.open_access_filer_api.routes.root import router as InfoRouter

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
    # default_response_class=ResponseModel,
    # openapi_tags=ROUTE_TAGS,
)

app.add_middleware(CorrelationIdMiddleware, header_name="X-Request-ID")

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


# --------------------------------------------------------------
# CHIILD ROUTES
# --------------------------------------------------------------

app.include_router(InfoRouter)
"""
app.include_router(TrackRouter)
app.include_router(MetadataRouter)
app.include_router(DataRouter)
app.include_router(ServiceRouter)
app.include_router(CollectionRouter)
app.include_router(QTLRouter)
"""
