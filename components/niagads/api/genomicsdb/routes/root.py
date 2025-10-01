import functools
from typing import Union
from fastapi import APIRouter, Depends, Request, Response
from niagads.api.common.app.factory import AppFactory
from niagads.api.common.constants import SharedOpenAPITags


from niagads.api.common.models.records import Entity, RecordSummary
from niagads.api.common.models.response.core import (
    MessageResponse,
    RecordResponse,
)
from niagads.api.common.models.routes import RouteDescription
from niagads.api.common.services.metadata.query import MetadataQueryService

from niagads.api.genomicsdb.dependencies import (
    TRACK_DATA_STORES,
    InternalRequestParameters,
)
from niagads.api.genomicsdb.documentation import (
    OPEN_API_TAGS,
    PUBMED_IDS,
    APP_NAME,
)


router = APIRouter(tags=[APP_NAME])


@router.get(
    "/status",
    response_model=Union[MessageResponse, RecordResponse],
    summary="get-api-info",
    description=f"Retrieve a brief overesponse_view of the {APP_NAME}",
    tags=[str(SharedOpenAPITags.STATUS)],
)
async def get_database_description(
    internal: InternalRequestParameters = Depends(),
) -> Union[MessageResponse, RecordResponse]:

    # TODO: genes, variants
    track_count = await MetadataQueryService(
        internal.session, data_store=TRACK_DATA_STORES
    ).get_track_count()

    result = RouteDescription(
        name=APP_NAME,
        description=OPEN_API_TAGS[1].description,
        url=OPEN_API_TAGS[1].externalDocs.get("url"),
        pubmed_id=PUBMED_IDS,
        records=[RecordSummary(entity=Entity.TRACK, num_records=track_count)],
    )
    return MessageResponse(
        message=["Database Statistics currently being updated; check back soon"],
        request=internal.request_data,
    )


@router.get(
    "/openapi.yaml",
    tags=[str(SharedOpenAPITags.STATUS)],
    name="get-specification-yaml",
    description="Get API Specificiation in `YAML` format",
    include_in_schema=False,
)
@functools.lru_cache()
def read_openapi_yaml(request: Request) -> Response:
    return Response(
        AppFactory.get_openapi_yaml(request.app),
        media_type="text/yaml",
    )
