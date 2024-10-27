from fastapi import APIRouter, Depends, Query
from fastapi.exceptions import RequestValidationError
from typing import Annotated, Optional, Union

from api.common.exceptions import RESPONSES
from api.dependencies.parameters.filters import ExpressionType, FilterParameter
from api.dependencies.parameters.location import span_param
from api.dependencies.parameters.optional import counts_only_param, format_param, keyword_param
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
@router.get("/", tags=tags,
    name="Get data from multiple tracks", response_model=Union[BEDResponse, BaseResponseModel],
    description="retrieve data from one or more FILER tracks in the specified region")
async def get_track_data(
        track: str = Depends(query_track_id),
        span: str = Depends(span_param),
        format: str = Depends(format_param),
        countsOnly: Optional[bool]=Depends(counts_only_param),
        internal: InternalRequestParameters = Depends()
        ) -> Union[BEDResponse, BaseResponseModel]:
    responseModel = BaseResponseModel if countsOnly else BEDResponse
    opts = HelperParameters(internal=internal, format=format, model=responseModel, 
        parameters=Parameters(track=track, span=span, countsOnly=countsOnly))
    return await __get_track_data(opts)

@router.get("/summary", tags=tags,
    name="Get a summary of data from multiple tracks", response_model=FILERTrackBriefResponse,
    description="retrieve a summary of track data (brief metadata and counts) from FILER tracks in the specified region")
async def get_track_data_summary(
        track: str = Depends(query_track_id),
        span: str = Depends(span_param),
        format: str = Depends(format_param),
        internal: InternalRequestParameters = Depends()
        ) -> FILERTrackBriefResponse:
    opts = HelperParameters(internal=internal, format=format, model=FILERTrackBriefResponse, 
        parameters=Parameters(track=track, span=span, summarize=True))
    return await __get_track_data(opts)

@router.get("/search", tags=tags,
    name="Get a summary of data from multiple tracks", response_model=FILERTrackBriefResponse,
    description="retrieve a summary of track data (brief metadata and counts) from FILER tracks in the specified region")
async def get_track_data_summary(
        track: str = Depends(query_track_id),
        span: str = Depends(span_param),
        format: str = Depends(format_param),
        internal: InternalRequestParameters = Depends()
        ) -> FILERTrackBriefResponse:
    opts = HelperParameters(internal=internal, format=format, model=FILERTrackBriefResponse, 
        parameters=Parameters(track=track, span=span, summarize=True))
    return await __get_track_data(opts)


@router.get("/search/summary", tags=tags,
    name="Get a summary of data from multiple tracks", response_model=FILERTrackBriefResponse,
    description="retrieve a summary of track data (brief metadata and counts) from FILER tracks in the specified region")
async def get_track_data_summary(
        track: str = Depends(query_track_id),
        span: str = Depends(span_param),
        format: str = Depends(format_param),
        internal: InternalRequestParameters = Depends()
        ) -> FILERTrackBriefResponse:
    opts = HelperParameters(internal=internal, format=format, model=FILERTrackBriefResponse, 
        parameters=Parameters(track=track, span=span, summarize=True))
    return await __get_track_data(opts)
