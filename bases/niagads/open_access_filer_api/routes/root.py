import functools
from typing import Union

from fastapi import APIRouter, Depends, Query, Request, Response
from niagads.open_access_api_common.app import AppFactory
from niagads.open_access_api_common.config.constants import SharedOpenAPITags
from niagads.open_access_api_common.config.core import Settings
from niagads.open_access_api_common.models.records.features.bed import BEDResponse
from niagads.open_access_api_common.models.records.route import (
    RecordSummary,
    RouteDescription,
)
from niagads.open_access_api_common.models.records.track.track import (
    TrackResponse,
    TrackSummaryResponse,
)
from niagads.open_access_api_common.models.response.core import (
    PagedResponseModel,
    ResponseModel,
)
from niagads.open_access_api_common.models.views.table.core import TableViewResponse
from niagads.open_access_api_common.parameters.location import span_param
from niagads.open_access_api_common.parameters.pagination import page_param
from niagads.open_access_api_common.parameters.record.query import track_list_param
from niagads.open_access_api_common.parameters.response import (
    ResponseContent,
    ResponseFormat,
    ResponseView,
)
from niagads.open_access_api_common.services.metadata.query import MetadataQueryService
from niagads.open_access_api_common.services.route import (
    Parameters,
    ResponseConfiguration,
)
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
from niagads.open_access_filer_api.services.route import FILERRouteHelper

router = APIRouter(tags=[ROUTE_NAME])


@router.get(
    "/",
    response_model=ResponseModel,
    name="About the " + ROUTE_NAME,
    description="brief summary about the " + ROUTE_NAME,
    tags=[str(SharedOpenAPITags.ABOUT)],
)
async def get_database_description(
    internal: InternalRequestParameters = Depends(),
) -> ResponseModel:

    trackCount = await MetadataQueryService(
        internal.session, dataStore=TRACK_DATA_STORES
    ).get_track_count()

    result = RouteDescription(
        name=ROUTE_NAME,
        description=OPEN_API_TAGS[0].description,
        url=OPEN_API_TAGS[0].externalDocs.get("url"),
        pubmed_id=PUBMED_IDS,
        records=[RecordSummary(record_type=RecordType.TRACK, num_records=trackCount)],
    )
    return ResponseModel(data=result, request=internal.requestData)


@router.get(
    "/openapi.yaml",
    tags=[str(SharedOpenAPITags.SPECIFICATION)],
    name="Specification: `YAML`",
    description="Get API Specificiation in `YAML` format",
    include_in_schema=False,
)
@functools.lru_cache()
def read_openapi_yaml(request: Request) -> Response:
    prefix = f"/{Settings.from_env().get_major_version()}/filer"
    return Response(
        AppFactory.get_openapi_yaml(request.app),
        media_type="text/yaml",
    )


tags = [
    str(SharedOpenAPITags.RECORD_BY_ID),
    str(SharedOpenAPITags.TRACK_RECORD),
]


@router.get(
    "/metadata",
    tags=tags,
    response_model=Union[
        TrackResponse, TrackSummaryResponse, TableViewResponse, ResponseModel
    ],
    name="Get metadata for multiple tracks",
    description="retrieve full metadata for one or more FILER track records by identifier",
)
async def get_track_metadata(
    track: str = Depends(track_list_param),
    content: str = Query(
        ResponseContent.FULL,
        description=ResponseContent.descriptive(inclUrls=True, description=True),
    ),
    format: str = Query(
        ResponseFormat.JSON, description=ResponseFormat.generic(description=True)
    ),
    view: str = Query(
        ResponseView.DEFAULT, description=ResponseView.table(description=True)
    ),
    internal: InternalRequestParameters = Depends(),
) -> Union[TrackSummaryResponse, TrackResponse, TableViewResponse, ResponseModel]:

    rContent = ResponseContent.descriptive(inclUrls=True).validate(
        content, "content", ResponseContent
    )
    helper = FILERRouteHelper(
        internal,
        ResponseConfiguration(
            format=ResponseFormat.generic().validate(format, "format", ResponseFormat),
            view=ResponseView.table().validate(view, "view", ResponseView),
            content=rContent,
            model=(
                TrackResponse
                if rContent == ResponseContent.FULL
                else (
                    TrackSummaryResponse
                    if rContent == ResponseContent.SUMMARY
                    else ResponseModel
                )
            ),
        ),
        Parameters(track=track),
    )
    return await helper.get_track_metadata()


tags = [
    str(SharedOpenAPITags.RECORD_BY_ID),
    str(SharedOpenAPITags.RECORD_BY_REGION),
    str(SharedOpenAPITags.TRACK_RECORD),
    str(SharedOpenAPITags.TRACK_DATA),
]


@router.get(
    "/data",
    tags=tags,
    name="Get data from multiple tracks",
    response_model=Union[
        BEDResponse, PagedResponseModel, TrackSummaryResponse, TableViewResponse
    ],
    description="retrieve data from one or more FILER tracks in the specified region",
)
async def get_track_data(
    track: str = Depends(track_list_param),
    span: str = Depends(span_param),
    page: int = Depends(page_param),
    content: str = Query(
        ResponseContent.FULL, description=ResponseContent.data(description=True)
    ),
    format: str = Query(
        ResponseFormat.JSON,
        description=ResponseFormat.functional_genomics(description=True),
    ),
    view: str = Query(ResponseView.DEFAULT, description=ResponseView.get_description()),
    internal: InternalRequestParameters = Depends(),
) -> Union[BEDResponse, PagedResponseModel, TrackSummaryResponse, TableViewResponse]:

    rContent = ResponseContent.data().validate(content, "content", ResponseContent)
    helper = FILERRouteHelper(
        internal,
        ResponseConfiguration(
            format=ResponseFormat.functional_genomics().validate(
                format, "format", ResponseFormat
            ),
            content=rContent,
            view=ResponseView.validate(view, "view", ResponseView),
            model=(
                BEDResponse
                if rContent == ResponseContent.FULL
                else (
                    TrackSummaryResponse
                    if rContent == ResponseContent.SUMMARY
                    else PagedResponseModel
                )
            ),
        ),
        Parameters(track=track, span=span, page=page),
    )

    return await helper.get_track_data()
