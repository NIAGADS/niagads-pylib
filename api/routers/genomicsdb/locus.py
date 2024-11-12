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
from api.response_models.base_models import BaseResponseModel
from api.response_models.data_models import BEDResponse
from api.routers.filer.models.track_response_model import FILERTrackBriefResponse, FILERTrackResponse

# TAGS = ROUTE_TAGS
router = APIRouter(
    prefix="/data",
#     tags=TAGS,
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
    pass