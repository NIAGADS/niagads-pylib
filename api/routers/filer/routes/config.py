from fastapi import APIRouter, Depends, Query
from fastapi.exceptions import RequestValidationError
from typing import Annotated, List, Optional, Union

from api.common.enums import ResponseContent
from api.common.exceptions import RESPONSES
from api.common.formatters import print_enum_values
from api.dependencies.parameters.filters import ExpressionType, FilterParameter
from api.dependencies.parameters.location import Assembly, assembly_param
from api.dependencies.parameters.optional import PaginationParameters, format_param, get_response_content, keyword_param, validate_response_content
from api.models import GenomeBrowserConfigResponse, GenomeBrowserExtendedConfigResponse
from api.common.helpers import Parameters
from api.models.base_models import BaseResponseModel

from ..common.helpers import HelperParameters, get_track_metadata as __get_track_metadata, search_track_metadata as __search_track_metadata
from ..common.constants import ROUTE_TAGS, TRACK_SEARCH_FILTER_FIELD_MAP
from ..dependencies import InternalRequestParameters, query_track_id

# TAGS = ROUTE_TAGS
router = APIRouter(
    prefix="/config",
#     tags=TAGS,
    responses=RESPONSES
)

tags = ["NIAGADS Genome Browser Configuration"]
@router.get("/igvbrowser", tags=tags, response_model=Union[GenomeBrowserConfigResponse, GenomeBrowserExtendedConfigResponse],
    name="Get Genome Browser configuration for multiple tracks by ID",
    description="retrieve NIAGADS Genome Browser track configuration for one or more FILER `track`(s)")
async def get_track_browser_config(
        # pagination: Annotated[PaginationParameters, Depends(PaginationParameters)],
        track = Depends(query_track_id),
        inclMetadata: Optional[bool] = Query(default=False, description="include filterable track metadata for the track selector display"),
        format: str= Depends(format_param),
        internal: InternalRequestParameters = Depends()
        ) -> Union[GenomeBrowserConfigResponse, GenomeBrowserExtendedConfigResponse]:

    responseModel = GenomeBrowserExtendedConfigResponse if inclMetadata \
        else GenomeBrowserConfigResponse
    opts = HelperParameters(internal=internal, 
        format=format, model=responseModel, # pagination=pagination,
        parameters=Parameters(track=track))
    return await __get_track_metadata(opts)


tags = tags + ['Record(s) by Text Search']
filter_param = FilterParameter(TRACK_SEARCH_FILTER_FIELD_MAP, ExpressionType.TEXT)
search_track_config_content_enum = get_response_content(exclude=[ResponseContent.IDS, ResponseContent.SUMMARY])
@router.get("/igvbrowser/search", tags=tags, response_model=Union[BaseResponseModel, GenomeBrowserConfigResponse, GenomeBrowserExtendedConfigResponse],
    name="Get Genome Browser configuration for multiple tracks by Search",
    description="retrieve NIAGADS Genome Browser track configuration for one or more FILER `track`(s) identified by keyword search or filters")
async def search_track_metadata(
        # pagination: Annotated[PaginationParameters, Depends(PaginationParameters)],
        assembly: Assembly = Depends(assembly_param), 
        filter = Depends(filter_param), 
        keyword: str = Depends(keyword_param),
        format: str= Depends(format_param),
        inclMetadata: Optional[bool] = Query(default=False, description="include filterable track metadata for the track selector display"),
        content: str = Query(ResponseContent.FULL, description=f'response content; one of: {print_enum_values(search_track_config_content_enum)}'),
        internal: InternalRequestParameters = Depends(),
        ) -> Union[BaseResponseModel, GenomeBrowserConfigResponse, GenomeBrowserExtendedConfigResponse]:
    
    if filter is None and keyword is None:
        raise RequestValidationError('must specify either a `filter` and/or a `keyword` to search')
    
    content = await validate_response_content(search_track_config_content_enum, content)
    responseModel = BaseResponseModel
    if content == ResponseContent.FULL:
        responseModel = GenomeBrowserExtendedConfigResponse if inclMetadata \
            else GenomeBrowserConfigResponse
            
    opts = HelperParameters(internal=internal, # pagination=pagination,
        content=content,
        format=format, model=responseModel,
        parameters=Parameters(assembly=assembly, filter=filter, keyword=keyword))
    
    return await __search_track_metadata(opts)
