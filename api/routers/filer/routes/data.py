from fastapi import APIRouter, Depends, Query
from fastapi.exceptions import RequestValidationError
from typing import Annotated, Optional, Union

from api.common.enums import ResponseContent
from api.common.exceptions import RESPONSES
from api.common.formatters import print_enum_values
from api.dependencies.parameters.filters import ExpressionType, FilterParameter
from api.dependencies.parameters.location import span_param
from api.dependencies.parameters.optional import format_param, get_response_content, keyword_param, validate_response_content
from api.common.helpers import Parameters
from api.response_models.base_models import BaseResponseModel
from api.response_models.data_models import BEDResponse
from api.routers.filer.models.track_response_model import FILERTrackBriefResponse

from ..common.helpers import HelperParameters, get_track_data as __get_track_data
from ..common.constants import ROUTE_TAGS, TRACK_SEARCH_FILTER_FIELD_MAP
from ..dependencies import InternalRequestParameters, query_track_id

TAGS = ROUTE_TAGS
router = APIRouter(
    prefix="/data",
    tags=TAGS,
    responses=RESPONSES
)

tags = TAGS + ["Track Data by ID"]
content_enum = get_response_content(exclude=[ResponseContent.IDS])
@router.get("/", tags=tags,
    name="Get data from multiple tracks", response_model=Union[BEDResponse, BaseResponseModel, FILERTrackBriefResponse],
    description="retrieve data from one or more FILER tracks in the specified region")
async def get_track_data(
        track: str = Depends(query_track_id),
        span: str = Depends(span_param),
        format: str = Depends(format_param),
        content: str = Query(ResponseContent.FULL, description=f'response content; one of: {print_enum_values(content_enum)}'),
        internal: InternalRequestParameters = Depends()
        ) -> Union[BEDResponse, BaseResponseModel, FILERTrackBriefResponse]:
    
    content = await validate_response_content(content_enum, content)
    responseModel = BEDResponse if content == ResponseContent.FULL \
        else FILERTrackBriefResponse if content == ResponseContent.SUMMARY \
            else BaseResponseModel
    opts = HelperParameters(internal=internal, format=format, 
            content=content, model=responseModel, 
        parameters=Parameters(track=track, span=span))
    return await __get_track_data(opts)


@router.get("/search", tags=tags,
    name="Get a summary of data from multiple tracks", response_model=Union[BEDResponse, BaseResponseModel, FILERTrackBriefResponse],
    description="retrieve a summary of track data (brief metadata and counts) from FILER tracks in the specified region")
async def get_track_data_summary(
        track: str = Depends(query_track_id),
        span: str = Depends(span_param),
        format: str = Depends(format_param),
        content: str = Query(ResponseContent.FULL, description=f'response content; one of: {print_enum_values(content_enum)}'),
        internal: InternalRequestParameters = Depends()
        ) -> Union[BEDResponse, BaseResponseModel, FILERTrackBriefResponse]:
    
    content = await validate_response_content(content_enum, content)
    responseModel = BEDResponse if content == ResponseContent.FULL \
        else FILERTrackBriefResponse if content == ResponseContent.SUMMARY \
            else BaseResponseModel
    opts = HelperParameters(internal=internal, format=format, model=responseModel,
        content = content, 
        parameters=Parameters(track=track, span=span, summarize=True))
    return await __get_track_data(opts)


