import functools

from fastapi import APIRouter, Depends, Request, Response
from niagads.api_common.app.factory import AppFactory
from niagads.api_common.constants import SharedOpenAPITags

from niagads.api_common.models.records import Entity, RecordSummary
from niagads.api_common.models.response.core import RecordResponse
from niagads.api_common.models.routes import RouteDescription
from niagads.api_common.services.metadata.query import MetadataQueryService

from niagads.filer_api.dependencies import (
    TRACK_DATA_STORES,
    InternalRequestParameters,
)
from niagads.filer_api.documentation import (
    APP_NAME,
    BASE_TAGS,
    OPEN_API_TAGS,
    PUBMED_IDS,
)

router = APIRouter(tags=BASE_TAGS)


@router.get(
    "/status",
    response_model=RecordResponse,
    summary="get-api-info",
    description=f"Retrieve a brief overesponse_view of the {APP_NAME}",
    tags=[str(SharedOpenAPITags.STATUS)],
)
async def get_database_description(
    internal: InternalRequestParameters = Depends(),
) -> RecordResponse:

    trackCount = await MetadataQueryService(
        internal.session, data_store=TRACK_DATA_STORES
    ).get_track_count()

    result = RouteDescription(
        name=APP_NAME,
        description=OPEN_API_TAGS[1].description,
        url=OPEN_API_TAGS[1].externalDocs.get("url"),
        pubmed_id=PUBMED_IDS,
        records=[RecordSummary(entity=Entity.TRACK, num_records=trackCount)],
    )
    return RecordResponse(data=[result], request=internal.request_data)


@router.get(
    "/openapi.yaml",
    tags=[str(SharedOpenAPITags.STATUS)],
    summary="get-specification-yaml",
    description="Get API Specificiation in `YAML` format",
    include_in_schema=False,
)
@functools.lru_cache()
def read_openapi_yaml(request: Request) -> Response:
    return Response(
        AppFactory.get_openapi_yaml(request.app),
        media_type="text/yaml",
    )
