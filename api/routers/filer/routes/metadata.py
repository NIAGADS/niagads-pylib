from fastapi import APIRouter, Depends, Query
from fastapi.exceptions import RequestValidationError
from typing import Annotated, Union

from api.common.enums import ResponseContent
from api.common.exceptions import RESPONSES
from api.common.formatters import print_enum_values
from api.common.helpers import Parameters, ResponseConfiguration
from api.dependencies.parameters.filters import ExpressionType, FilterParameter
from api.dependencies.parameters.location import Assembly, assembly_param
from api.dependencies.parameters.optional import PaginationParameters, get_response_content, keyword_param, validate_response_content
from api.models.base_models import BaseResponseModel

from ..common.helpers import FILERRouteHelper
from ..common.constants import TRACK_SEARCH_FILTER_FIELD_MAP
from ..models.response.filer_track import FILERTrackBriefResponse, FILERTrackResponse
from ..dependencies.parameters import InternalRequestParameters, query_track_id, non_data_format_param

router = APIRouter(prefix="/metadata", responses=RESPONSES)

tags = ["Track Metadata by ID"]
get_track_metadata_content_enum = get_response_content(exclude=[ResponseContent.IDS, ResponseContent.COUNTS])
@router.get("/", tags=tags, response_model=Union[FILERTrackResponse, FILERTrackBriefResponse],
    name="Get metadata for multiple tracks",
    description="retrieve full metadata for one or more FILER track records")
async def get_track_metadata(
        track: str = Depends(query_track_id),
        format: str= Depends(non_data_format_param),
        content: str = Query(ResponseContent.FULL, description=f'response content; one of: {print_enum_values(get_track_metadata_content_enum)}'),
        internal: InternalRequestParameters = Depends()) -> Union[FILERTrackBriefResponse, FILERTrackResponse]:
    
    rContent = validate_response_content(get_track_metadata_content_enum, content)
    helper = FILERRouteHelper(
        internal,
        ResponseConfiguration(
            format=format,
            content=rContent,
            model=FILERTrackResponse if rContent == ResponseContent.FULL \
                else FILERTrackBriefResponse 
        ), 
        Parameters(track=track)
    )
    return await helper.get_track_metadata()

tags = ['Record(s) by Text Search'] + ['Track Metadata by Text Search']
filter_param = FilterParameter(TRACK_SEARCH_FILTER_FIELD_MAP, ExpressionType.TEXT)
@router.get("/search", tags=tags, response_model=Union[BaseResponseModel, FILERTrackBriefResponse, FILERTrackResponse],
    name="Search for tracks", 
    description="find functional genomics tracks using category filters or by a keyword search against all text fields in the track metadata")
async def search_track_metadata(
        pagination: Annotated[PaginationParameters, Depends(PaginationParameters)],
        assembly: Assembly = Depends(assembly_param), 
        filter = Depends(filter_param), 
        keyword: str = Depends(keyword_param),
        format: str= Depends(non_data_format_param),
        content: str = Query(ResponseContent.FULL, description=f'response content; one of: {print_enum_values(ResponseContent)}'),
        internal: InternalRequestParameters = Depends(),
        ) -> Union[BaseResponseModel, FILERTrackBriefResponse, FILERTrackResponse]:
    
    if filter is None and keyword is None:
        raise RequestValidationError('must specify either a `filter` and/or a `keyword` to search')
    
    rContent = validate_response_content(ResponseContent, content)
    helper = FILERRouteHelper(
        internal,
        ResponseConfiguration(
            format=format,
            content=rContent,
            model=FILERTrackResponse if rContent == ResponseContent.FULL \
                else FILERTrackBriefResponse if rContent == ResponseContent.SUMMARY \
                    else BaseResponseModel
        ),
        Parameters(
            page=pagination.page,
            assembly=assembly,
            filter=filter,
            keyword=keyword)
    )
    
    return await helper.search_track_metadata()

