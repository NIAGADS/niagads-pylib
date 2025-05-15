import functools
from fastapi import APIRouter, Depends, Request, Response
from niagads.open_access_api_common.models.records.route import (
    RecordSummary,
    RouteDescription,
)
from niagads.open_access_api_common.models.response.core import ResponseModel
from niagads.open_access_api_common.services.metadata.query import MetadataQueryService
from niagads.open_access_api_common.types import RecordType
from niagads.open_access_api_common.utils import get_openapi_yaml
from niagads.open_access_filer_api.dependencies import TRACK_DATA_STORES
from niagads.open_access_genomics_api.dependencies import InternalRequestParameters
from niagads.open_access_genomics_api.documentation import (
    OPEN_API_TAGS,
    PUBMED_IDS,
    ROUTE_NAME,
)


router = APIRouter()


@router.get(
    "/",
    response_model=ResponseModel,
    description="brief summary about the " + ROUTE_NAME,
    tags=["Service Information"],
)
async def get_database_description(
    internal: InternalRequestParameters = Depends(),
) -> ResponseModel:

    trackCount = await MetadataQueryService(
        internal.session, dataStore=TRACK_DATA_STORES
    ).get_track_count()

    result = RouteDescription(
        name=ROUTE_NAME,
        description=OPEN_API_TAGS.description,
        url=OPEN_API_TAGS.externalDocs.get("url"),
        pubmed_id=PUBMED_IDS,
        records=[RecordSummary(record_type=RecordType.TRACK, num_records=trackCount)],
    )
    return ResponseModel(data=result, request=internal.requestData)


@router.get(
    "/openapi.yaml",
    tags=["OpenAPI Specification"],
    name="Specification: `YAML`",
    description="Get API Specificiation in `YAML` format",
)
@functools.lru_cache()
def read_openapi_yaml(request: Request) -> Response:
    return get_openapi_yaml(request)