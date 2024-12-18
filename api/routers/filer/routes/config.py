from fastapi import APIRouter, Depends, Query
from fastapi.exceptions import RequestValidationError
from typing import Optional, Union

from api.common.enums import ResponseContent
from api.common.exceptions import RESPONSES
from api.common.formatters import print_enum_values
from api.dependencies.parameters.filters import ExpressionType, FilterParameter
from api.dependencies.parameters.location import Assembly, assembly_param
from api.dependencies.parameters.optional import format_param, get_response_content, keyword_param, validate_response_content
from api.models import IGVBrowserConfigResponse, IGVBrowserExtendedConfigResponse
from api.common.helpers import Parameters, ResponseConfiguration
from api.models.base_models import BaseResponseModel

from ..common.enums import METADATA_CONTENT_ENUM
from ..common.helpers import FILERRouteHelper
from ..common.constants import TRACK_SEARCH_FILTER_FIELD_MAP
from ..dependencies.parameters import InternalRequestParameters, query_track_id

router = APIRouter(prefix="/config", responses=RESPONSES)

tags = ["NIAGADS Genome Browser Configuration"]

@router.get("/igvbrowser", tags=tags, response_model=Union[IGVBrowserConfigResponse, IGVBrowserExtendedConfigResponse],
    name="Get Genome Browser configuration for multiple tracks by ID",
    description="retrieve NIAGADS Genome Browser track configuration for one or more FILER `track`(s)")
async def get_track_browser_config(
        track = Depends(query_track_id),
        content: str = Query(ResponseContent.SUMMARY, description=f'response content; one of: {print_enum_values(METADATA_CONTENT_ENUM)}'),
        internal: InternalRequestParameters = Depends()
        ) -> Union[IGVBrowserConfigResponse, IGVBrowserExtendedConfigResponse]:

    rContent = validate_response_content(METADATA_CONTENT_ENUM, content)
    helper = FILERRouteHelper(
        internal,
        ResponseConfiguration(
            content=rContent,
            model=IGVBrowserExtendedConfigResponse if rContent == ResponseContent.FULL \
                else IGVBrowserConfigResponse
        ),
        Parameters(track=track)
    )

    return await helper.get_track_metadata()


tags = tags + ['Record(s) by Text Search']
filter_param = FilterParameter(TRACK_SEARCH_FILTER_FIELD_MAP, ExpressionType.TEXT)
@router.get("/igvbrowser/search", tags=tags, response_model=Union[BaseResponseModel, IGVBrowserConfigResponse, IGVBrowserExtendedConfigResponse],
    name="Get Genome Browser configuration for multiple tracks by Search",
    description="retrieve NIAGADS Genome Browser track configuration for one or more FILER `track`(s) identified by keyword search or filters")
async def search_track_metadata(
        assembly: Assembly = Depends(assembly_param), 
        filter = Depends(filter_param), 
        keyword: str = Depends(keyword_param),
        content: str = Query(ResponseContent.FULL, description=f'response content; one of: {print_enum_values(METADATA_CONTENT_ENUM)}'),
        internal: InternalRequestParameters = Depends(),
        ) -> Union[BaseResponseModel, IGVBrowserConfigResponse, IGVBrowserExtendedConfigResponse]:
    
    if filter is None and keyword is None:
        raise RequestValidationError('must specify a `filter` and/or a `keyword` to search')
    
    rContent = validate_response_content(METADATA_CONTENT_ENUM, content)
    helper = FILERRouteHelper(
        internal,
        ResponseConfiguration(
            content=rContent,
            model=IGVBrowserExtendedConfigResponse if rContent == ResponseContent.FULL \
                else IGVBrowserConfigResponse
        ),
        Parameters(assembly=assembly, filter=filter, keyword=keyword)
    )
    
    return await helper.search_track_metadata()
