from fastapi import APIRouter, Depends, Query
from fastapi.exceptions import RequestValidationError
from typing import Annotated, List, Optional, Union

from api.common.enums import ResponseContent
from api.common.exceptions import RESPONSES
from api.common.formatters import print_enum_values
from api.dependencies.parameters.filters import ExpressionType, FilterParameter
from api.dependencies.parameters.location import Assembly, assembly_param
from api.dependencies.parameters.optional import PaginationParameters, format_param, get_response_content, keyword_param, validate_response_content
from api.response_models import GenomeBrowserConfigResponse, GenomeBrowserExtendedConfigResponse
from api.common.helpers import Parameters
from api.response_models.base_models import BaseResponseModel

from ..common.helpers import HelperParameters, get_track_metadata as __get_track_metadata, search_track_metadata as __search_track_metadata
from ..common.constants import ROUTE_TAGS, TRACK_SEARCH_FILTER_FIELD_MAP
from ..models.track_response_model import FILERTrackBriefResponse, FILERTrackResponse
from ..dependencies import InternalRequestParameters, query_track_id

TAGS = ROUTE_TAGS
router = APIRouter(
    prefix="/metadata",
    tags=TAGS,
    responses=RESPONSES
)

tags = TAGS + ["Track Metadata by ID"]
content_enum = get_response_content(exclude=[ResponseContent.IDS, ResponseContent.COUNTS])
@router.get("/", tags=tags, response_model=Union[FILERTrackResponse, FILERTrackBriefResponse],
    name="Get metadata for multiple tracks",
    description="retrieve full metadata for one or more FILER track records")
async def get_track_metadata(
        track: str = Depends(query_track_id),
        format: str= Depends(format_param),
        content: str = Query(ResponseContent.FULL, description=f'response content; one of: {print_enum_values(content_enum)}'),
        internal: InternalRequestParameters = Depends()) -> Union[FILERTrackBriefResponse, FILERTrackResponse]:
    
    content = await validate_response_content(content_enum, content)
    responseModel = FILERTrackResponse if content == ResponseContent.FULL \
        else FILERTrackBriefResponse 
    
    opts = HelperParameters(internal=internal, 
        format=format, content=content,
        model=responseModel, parameters=Parameters(track=track))
    return await __get_track_metadata(opts)

tags = TAGS + ['Record(s) by Text Search'] + ['Track Metadata by Text Search']
filter_param = FilterParameter(TRACK_SEARCH_FILTER_FIELD_MAP, ExpressionType.TEXT)
content_enum = ResponseContent # can get all responses for this request (counts, ids, brief, full)
@router.get("/search", tags=tags, response_model=Union[BaseResponseModel, FILERTrackBriefResponse, FILERTrackResponse],
    name="Search for tracks", 
    description="find functional genomics tracks using category filters or by a keyword search against all text fields in the track metadata")
async def search_track_metadata(
        pagination: Annotated[PaginationParameters, Depends(PaginationParameters)],
        assembly: Assembly = Depends(assembly_param), 
        filter = Depends(filter_param), 
        keyword: str = Depends(keyword_param),
        format: str= Depends(format_param),
        content: str = Query(ResponseContent.FULL, description=f'response content; one of: {print_enum_values(content_enum)}'),
        internal: InternalRequestParameters = Depends(),
        ) -> Union[BaseResponseModel, FILERTrackBriefResponse, FILERTrackResponse]:
    
    if filter is None and keyword is None:
        raise RequestValidationError('must specify either a `filter` and/or a `keyword` to search')
    
    content = await validate_response_content(content_enum, content)
    responseModel = FILERTrackResponse if content == ResponseContent.FULL \
        else FILERTrackBriefResponse if content == ResponseContent.SUMMARY \
            else BaseResponseModel
    
    opts = HelperParameters(internal=internal, pagination=pagination,
        content=content,
        format=format, model=responseModel,
        parameters=Parameters(assembly=assembly, filter=filter, keyword=keyword))
    
    return await __search_track_metadata(opts)


tags = TAGS + ["NIAGADS Genome Browser Configuration"]
@router.get("/browser_config", tags=tags,  response_model=Union[GenomeBrowserConfigResponse, GenomeBrowserExtendedConfigResponse],
    name="Get Genome Browser configuration for multiple tracks",
    description="retrieve NIAGADS Genome Browser track configuration for one or more FILER `track`(s) specified in the path")
async def get_track_browser_config(
        track = Depends(query_track_id),
        inclMetadata: Optional[bool] = Query(default=False, description="include filterable track metadata for the track selector display"),
        format: str= Depends(format_param),
        internal: InternalRequestParameters = Depends()
        ) -> Union[GenomeBrowserConfigResponse, GenomeBrowserExtendedConfigResponse]:

    responseModel = GenomeBrowserExtendedConfigResponse if inclMetadata \
        else GenomeBrowserConfigResponse
    opts = HelperParameters(internal=internal, 
        format=format, model=responseModel, 
        parameters=Parameters(track=track))
    return await __get_track_metadata(opts)
