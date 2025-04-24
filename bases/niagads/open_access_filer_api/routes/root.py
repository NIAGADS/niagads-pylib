from fastapi import APIRouter, Depends
from niagads.open_access_api_common.models.records.route import (
    RecordSummary,
    RouteDescription,
)
from niagads.open_access_api_common.models.response.core import ResponseModel
from niagads.open_access_api_common.services.metadata.query import MetadataQueryService
from niagads.open_access_api_common.types import RecordType
from niagads.open_access_filer_api.dependencies import (
    TRACK_DATA_STORES,
    InternalRequestParameters,
)
from niagads.open_access_filer_api.documentation import (
    OPEN_API_TAGS,
    PUBMED_IDS,
    ROUTE_NAME,
)

ROUTE_BASE_TAG = ["Route Information"]

router = APIRouter(tags=ROUTE_BASE_TAG)


@router.get(
    "/",
    name="about",
    response_model=ResponseModel,
    description="brief summary about the " + ROUTE_NAME,
)
async def get_route_description(
    internal: InternalRequestParameters = Depends(),
) -> ResponseModel:

    trackCount = await MetadataQueryService(
        internal.session, dataStore=TRACK_DATA_STORES
    ).get_track_count()

    result = RouteDescription(
        name=ROUTE_NAME,
        description=OPEN_API_TAGS["description"],
        url=OPEN_API_TAGS["externalDocs"]["url"],
        pubmed_id=PUBMED_IDS,
        records=[RecordSummary(record_type=RecordType.TRACK, num_records=trackCount)],
    )
    return ResponseModel(data=result, request=internal.requestData)
