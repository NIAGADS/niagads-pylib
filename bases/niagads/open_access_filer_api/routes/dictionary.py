from typing import List, Union
from fastapi import APIRouter, Depends, Query
from niagads.exceptions.core import ValidationError
from niagads.genome.core import Assembly
from niagads.open_access_api_common.config.constants import SharedOpenAPITags
from niagads.open_access_api_common.models.records.track.igvbrowser import (
    IGVBrowserTrackConfig,
    IGVBrowserTrackConfigResponse,
    IGVBrowserTrackSelectorResponse,
)
from niagads.open_access_api_common.models.records.track.track import (
    TrackResponse,
    AbridgedTrackResponse,
)
from niagads.open_access_api_common.models.response.core import GenericResponse
from niagads.open_access_api_common.parameters.location import (
    assembly_param,
    chromosome_param,
)

from niagads.open_access_api_common.parameters.record.query import (
    optional_track_list_param,
    track_param,
)
from niagads.open_access_api_common.parameters.response import (
    ResponseContent,
    ResponseFormat,
)
from niagads.open_access_api_common.services.metadata.query import MetadataQueryService
from niagads.open_access_api_common.services.route import (
    Parameters,
    ResponseConfiguration,
)
from niagads.open_access_filer_api.dependencies import (
    InternalRequestParameters,
    TextSearchFilterFields,
)
from niagads.open_access_filer_api.documentation import BASE_TAGS
from niagads.open_access_filer_api.services.route import FILERRouteHelper

router = APIRouter(prefix="/dictionary", tags=BASE_TAGS)

tags = [str(SharedOpenAPITags.ONTOLOGIES)]


@router.get(
    "/filters",
    tags=tags,
    response_model=Union[GenericResponse],
    summary="get-text-search-filter-fields",
    description="List allowable fields for text search filter expressions.",
)
async def get_allowable_text_filters(
    internal: InternalRequestParameters = Depends(),
) -> GenericResponse:

    return GenericResponse(
        data=TextSearchFilterFields.list(toLower=True), request=internal.requestData
    )


# TODO values for each filter field
"""
@router.get(
    "/filters/{field}",
    tags=tags,
    response_model=Union[GenericResponse],
    summary="get-text-search-filter-fields",
    description="List allowable fields for text search filter expressions.",
)
async def get_allowable_text_filters(
    internal: InternalRequestParameters = Depends(),
) -> GenericResponse:

    return GenericResponse(
        data=TextSearchFilterFields.list(toLower=True), request=internal.requestData
    )
"""
