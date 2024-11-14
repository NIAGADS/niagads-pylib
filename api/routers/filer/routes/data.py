from fastapi import APIRouter, Depends, Query
from fastapi.exceptions import RequestValidationError
from typing import Annotated, Optional, Union

from api.common.enums import Assembly, ResponseContent
from api.common.exceptions import RESPONSES
from api.common.formatters import print_enum_values
from api.dependencies.parameters.filters import ExpressionType, FilterParameter
from api.dependencies.parameters.location import assembly_param, span_param
from api.dependencies.parameters.optional import PaginationParameters, format_param, get_response_content, keyword_param, validate_response_content
from api.common.helpers import Parameters
from api.response_models.base_models import BaseResponseModel, PaginationDataModel
from api.response_models.data_models import BEDResponse

from ..common.helpers import HelperParameters, get_track_data as __get_track_data, search_track_data as __search_track_data
from ..common.constants import TRACK_SEARCH_FILTER_FIELD_MAP
from ..dependencies import InternalRequestParameters, query_track_id
from ..models.track_response_model import FILERTrackBriefResponse

router = APIRouter(
    prefix="/data",
    responses=RESPONSES
)

tags = ["Track Data by ID"]
get_track_data_content_enum = get_response_content(exclude=[ResponseContent.IDS])
@router.get("/", tags=tags,
    name="Get data from multiple tracks by ID", response_model=Union[BEDResponse, BaseResponseModel, FILERTrackBriefResponse],
    description="retrieve data from one or more FILER tracks in the specified region")
async def get_track_data(
        pagination: Annotated[PaginationParameters, Depends(PaginationParameters)],
        track: str = Depends(query_track_id),
        span: str = Depends(span_param),
        format: str = Depends(format_param),
        content: str = Query(ResponseContent.FULL, description=f'response content; one of: {print_enum_values(get_track_data_content_enum)}'),
        internal: InternalRequestParameters = Depends()
        ) -> Union[BEDResponse, BaseResponseModel, FILERTrackBriefResponse]:
    
    content = await validate_response_content(get_track_data_content_enum, content)
    responseModel = BEDResponse if content == ResponseContent.FULL \
        else FILERTrackBriefResponse if content == ResponseContent.SUMMARY \
            else BaseResponseModel
            
    opts = HelperParameters(internal=internal, format=format, 
            content=content, model=responseModel, pagination=PaginationDataModel(page=pagination.page),
        parameters=Parameters(track=track, span=span))
    return await __get_track_data(opts)


tags = ['Record(s) by Text Search'] + ['Track Data by Text Search']
filter_param = FilterParameter(TRACK_SEARCH_FILTER_FIELD_MAP, ExpressionType.TEXT)
@router.get("/search", tags=tags, response_model=Union[BaseResponseModel, FILERTrackBriefResponse, BEDResponse],
    name="Get data from multiple tracks by Search", 
    description="find functional genomics tracks using category filters or by a keyword search against all text fields in the track metadata")
async def get_track_data_by_metadata_search(
        pagination: Annotated[PaginationParameters, Depends(PaginationParameters)],
        assembly: Assembly = Depends(assembly_param), 
        span: str = Depends(span_param),
        filter = Depends(filter_param), 
        keyword: str = Depends(keyword_param),
        format: str= Depends(format_param),
        content: str = Query(ResponseContent.FULL, description=f'response content; one of: {print_enum_values(ResponseContent)}'),
        internal: InternalRequestParameters = Depends(),
        ) -> Union[BaseResponseModel, FILERTrackBriefResponse, BEDResponse]:
    
    if filter is None and keyword is None:
        raise RequestValidationError('must specify either a `filter` and/or a `keyword` to search')
    
    content = await validate_response_content(ResponseContent, content)
    responseModel = BEDResponse if content == ResponseContent.FULL \
        else FILERTrackBriefResponse if content == ResponseContent.SUMMARY \
            else BaseResponseModel
    
    opts = HelperParameters(internal=internal, pagination=PaginationDataModel(page=pagination.page),
        content=content,
        format=format, model=responseModel,
        parameters=Parameters(assembly=assembly, filter=filter, keyword=keyword, span=span))
    
    return await __search_track_data(opts)