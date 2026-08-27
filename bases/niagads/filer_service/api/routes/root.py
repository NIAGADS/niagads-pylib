import functools
from fastapi import APIRouter, Depends, Request, Response
from niagads.api.common.app.factory import AppFactory
from niagads.api.common.models.domain.entities.entity import Entity, EntityMetrics
from niagads.api.common.models.domain.routes import RouteDescriptor
from niagads.api.common.models.response.base import DataResponse
from niagads.api.common.services.metadata.query import MetadataQueryService
from niagads.filer_service.api.dependencies import FILEREndpointRequestParameters
from niagads.filer_service.api.documentation import APP_NAME, OPEN_API_TAGS, PUBMED_IDS

router = APIRouter(tags=["Status"])


@router.get(
    "/status",
    summary="get-api-status",
    description="Retrieve basic FILER API status and service information.",
    response_model=DataResponse,
)
async def get_status(
    internal: FILEREndpointRequestParameters = Depends(),
):
    track_metrics = await MetadataQueryService(
        internal.database_session,
    ).get_track_count()

    result = RouteDescriptor(
        name=APP_NAME,
        description=OPEN_API_TAGS[0].description,
        url=OPEN_API_TAGS[0].externalDocs.get("url"),
        pubmed_id=PUBMED_IDS,
        records=[EntityMetrics(entity=Entity.TRACK, num_records=track_metrics)],
    )
    return DataResponse(data=[result], request=internal.request_data)


@functools.lru_cache()
@router.get(
    "/openapi.yaml",
    summary="get-openapi-yaml",
    description="Retrieve the FILER OpenAPI specification in YAML format.",
    include_in_schema=False,
)
async def get_openapi_yaml(request: Request) -> Response:
    return Response(
        AppFactory.get_openapi_yaml(request.app),
        media_type="text/yaml",
    )
