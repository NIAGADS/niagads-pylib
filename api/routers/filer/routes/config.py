from fastapi import APIRouter, Depends, Query
from fastapi.exceptions import RequestValidationError
from typing import Optional, Union

from api.common.enums import ResponseContent
from api.common.exceptions import RESPONSES
from api.common.formatters import print_enum_values
from api.common.helpers import Parameters, ResponseConfiguration

from api.dependencies.parameters.filters import ExpressionType, FilterParameter
from api.dependencies.parameters.location import Assembly, assembly_param
from api.dependencies.parameters.optional import keyword_param, validate_response_content
from api.models.base_response_models import BaseResponseModel
from api.models.igvbrowser_config import IGVBrowserApplicationConfigResponse, IGVBrowserTrackConfigResponse


from ..common.enums import METADATA_CONTENT_ENUM
from ..common.helpers import FILERRouteHelper
from ..common.constants import TRACK_SEARCH_FILTER_FIELD_MAP
from ..dependencies.parameters import InternalRequestParameters, query_track_id

router = APIRouter(prefix="/config", responses=RESPONSES)

tags = ["NIAGADS Genome Browser Configuration"]

@router.get("/igvbrowser", tags=tags, response_model=Union[IGVBrowserTrackConfigResponse, IGVBrowserApplicationConfigResponse],
    name="Get Genome Browser configuration for multiple tracks by ID",
    description="retrieve NIAGADS Genome Browser track configuration for one or more FILER `track`(s)")
async def get_track_browser_config(
        track = Depends(query_track_id),
        trackSelector: bool = Query(default=False, description="include track selector table"),
        internal: InternalRequestParameters = Depends()
    ) -> Union[IGVBrowserApplicationConfigResponse, IGVBrowserApplicationConfigResponse]:

    helper = FILERRouteHelper(
        internal,
        ResponseConfiguration(
            content=ResponseContent.FULL if trackSelector else ResponseContent.SUMMARY,
            model=IGVBrowserApplicationConfigResponse if trackSelector \
                else IGVBrowserTrackConfigResponse
        ),
        Parameters(track=track)
    )

    return await helper.get_track_metadata()


tags = tags + ['Record(s) by Text Search']
filter_param = FilterParameter(TRACK_SEARCH_FILTER_FIELD_MAP, ExpressionType.TEXT)
@router.get("/igvbrowser/search", tags=tags, response_model=Union[BaseResponseModel, IGVBrowserApplicationConfigResponse, IGVBrowserTrackConfigResponse],
    name="Get Genome Browser configuration for multiple tracks by Search",
    description="retrieve NIAGADS Genome Browser track configuration for one or more FILER `track`(s) identified by keyword search or filters")
async def get_track_browser_config_by_metadata_search(
        assembly: Assembly = Depends(assembly_param), 
        filter = Depends(filter_param), 
        keyword: str = Depends(keyword_param),
        trackSelector: bool = Query(default=False, description="include track selector table"),
        internal: InternalRequestParameters = Depends(),
        ) -> Union[BaseResponseModel, IGVBrowserTrackConfigResponse, IGVBrowserApplicationConfigResponse]:
    
    if filter is None and keyword is None:
        raise RequestValidationError('must specify a `filter` and/or a `keyword` to search')
    
    helper = FILERRouteHelper(
        internal,
        ResponseConfiguration(
            content=ResponseContent.FULL if trackSelector else ResponseContent.SUMMARY,
            model=IGVBrowserApplicationConfigResponse if trackSelector \
                else IGVBrowserTrackConfigResponse
        ),
        Parameters(assembly=assembly, filter=filter, keyword=keyword)
    )
    
    return await helper.search_track_metadata()
