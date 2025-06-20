import functools

from fastapi import APIRouter, Depends, Request, Response
from niagads.open_access_api_common.app import AppFactory
from niagads.open_access_api_common.config.constants import SharedOpenAPITags
from niagads.open_access_api_common.config.core import Settings
from niagads.open_access_api_common.models.records.route import (
    RecordSummary,
    RouteDescription,
)
from niagads.open_access_api_common.models.response.core import GenericResponse
from niagads.open_access_api_common.services.metadata.query import MetadataQueryService
from niagads.open_access_api_common.types import RecordType
from niagads.open_access_filer_api.dependencies import (
    TRACK_DATA_STORES,
    InternalRequestParameters,
)
from niagads.open_access_filer_api.documentation import (
    APP_NAME,
    BASE_TAGS,
    OPEN_API_TAGS,
    PUBMED_IDS,
)

router = APIRouter(tags=BASE_TAGS)


@router.get(
    "/",
    response_model=GenericResponse,
    summary="get-api-info",
    description=f"Retrieve a brief overview of the {APP_NAME}",
    tags=[str(SharedOpenAPITags.DOCUMENTATION)],
)
async def get_database_description(
    internal: InternalRequestParameters = Depends(),
) -> GenericResponse:

    trackCount = await MetadataQueryService(
        internal.session, dataStore=TRACK_DATA_STORES
    ).get_track_count()

    result = RouteDescription(
        name=APP_NAME,
        description=OPEN_API_TAGS[1].description,
        url=OPEN_API_TAGS[1].externalDocs.get("url"),
        pubmed_id=PUBMED_IDS,
        records=[RecordSummary(record_type=RecordType.TRACK, num_records=trackCount)],
    )
    return GenericResponse(data=result, request=internal.requestData)


@router.get(
    "/openapi.yaml",
    tags=[str(SharedOpenAPITags.DOCUMENTATION)],
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
