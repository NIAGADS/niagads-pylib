from fastapi import APIRouter, Depends, Query
from fastapi.exceptions import RequestValidationError
from typing import Annotated, Union

from api.common.enums import Assembly, ResponseContent, ResponseFormat
from api.common.exceptions import RESPONSES
from api.common.formatters import print_enum_values
from api.common.helpers import Parameters, ResponseConfiguration

from api.dependencies.parameters.filters import ExpressionType, FilterParameter
from api.dependencies.parameters.location import assembly_param, span_param
from api.dependencies.parameters.optional import PaginationParameters, get_response_content, get_response_format, keyword_param, validate_response_content

from api.models.base_response_models import PagedResponseModel

from ..common.helpers import FILERRouteHelper
from ..common.constants import TRACK_SEARCH_FILTER_FIELD_MAP
from ..dependencies.parameters import InternalRequestParameters, required_query_track_id
from ..models.filer_track import FILERTrackBriefResponse
from ..models.bed_features import BEDResponse

router = APIRouter(prefix="/data", responses=RESPONSES)

DATA_FORMAT_ENUM = get_response_format(exclude=[ResponseFormat.VCF])


tags = ["Track Data by ID"]
get_track_data_content_enum = get_response_content(exclude=[ResponseContent.IDS, ResponseContent.URLS])

@router.get("/", tags=tags,
    name="Get data from multiple tracks by ID", response_model=Union[BEDResponse, PagedResponseModel, FILERTrackBriefResponse],
    description="retrieve data from one or more FILER tracks in the specified region")

async def get_track_data(
        pagination: Annotated[PaginationParameters, Depends(PaginationParameters)],
        track: str = Depends(required_query_track_id),
        span: str = Depends(span_param),
        format: str = Query(ResponseFormat.JSON, description=f'response content; one of: {print_enum_values(DATA_FORMAT_ENUM)}'),
        content: str = Query(ResponseContent.FULL, description=f'response content; one of: {print_enum_values(get_track_data_content_enum)}'),
        internal: InternalRequestParameters = Depends()
    ) -> Union[BEDResponse, PagedResponseModel, FILERTrackBriefResponse]:
    
    rContent = validate_response_content(get_track_data_content_enum, content)
    helper = FILERRouteHelper(
        internal,
        ResponseConfiguration(
            format=format,
            content=rContent,
            model=BEDResponse if rContent == ResponseContent.FULL \
                else FILERTrackBriefResponse if rContent == ResponseContent.SUMMARY \
                    else PagedResponseModel
        ), 
        Parameters(track=track, span=span, page=pagination.page)
    )
    
    return await helper.get_track_data()


tags = ['Record(s) by Text Search'] + ['Track Data by Text Search'] + ['Track Data by Genomic Region']
filter_param = FilterParameter(TRACK_SEARCH_FILTER_FIELD_MAP, ExpressionType.TEXT)
@router.get("/search", tags=tags, response_model=Union[PagedResponseModel, FILERTrackBriefResponse, BEDResponse],
    name="Get data from multiple tracks by Search", 
    description="find functional genomics tracks with data in specified region; qualify using category filters or by a keyword search against all text fields in the track metadata")
async def get_track_data_by_metadata_search(
        pagination: Annotated[PaginationParameters, Depends(PaginationParameters)],
        assembly: Assembly = Depends(assembly_param), 
        span: str = Depends(span_param),
        filter = Depends(filter_param), 
        keyword: str = Depends(keyword_param),
        format: str = Query(ResponseFormat.JSON, description=f'response content; one of: {print_enum_values(DATA_FORMAT_ENUM)}'),
        content: str = Query(ResponseContent.FULL, description=f'response content; one of: {print_enum_values(ResponseContent)}'),
        internal: InternalRequestParameters = Depends(),
        ) -> Union[PagedResponseModel, FILERTrackBriefResponse, BEDResponse]:
    
    # if filter is None and keyword is None:
    #     raise RequestValidationError('must specify a `filter` and/or a `keyword` to search')
    
    rContent = validate_response_content(ResponseContent, content)
    helper = FILERRouteHelper(
        internal,
        ResponseConfiguration(
            format=format,
            content=rContent,
            model=BEDResponse if rContent == ResponseContent.FULL \
                else FILERTrackBriefResponse if rContent == ResponseContent.SUMMARY \
                    else PagedResponseModel
        ),
        Parameters(assembly=assembly, filter=filter, keyword=keyword, span=span, page=pagination.page)
    )
    
    return await helper.search_track_data()