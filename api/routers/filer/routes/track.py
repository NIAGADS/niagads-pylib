from fastapi import APIRouter, Depends, Query
from typing import Union

from api.common.enums import ResponseContent
from api.common.exceptions import RESPONSES
from api.common.formatters import print_enum_values
from api.dependencies.parameters.location import span_param
from api.dependencies.parameters.optional import format_param, get_response_content, validate_response_content
from api.common.helpers import Parameters, ResponseConfiguration

from api.models import GenomeBrowserConfigResponse, GenomeBrowserExtendedConfigResponse, BEDResponse
from api.models.base_models import BaseResponseModel

from ..dependencies.parameters import InternalRequestParameters, path_track_id
from ..common.helpers import FILERRouteHelper
from ..common.enums import METADATA_CONTENT_ENUM, TRACK_DATA_CONTENT_ENUM
from ..models.response.filer_track import FILERTrackResponse, FILERTrackBriefResponse


router = APIRouter(prefix="/track", responses=RESPONSES)

tags = ["Record by ID", "Track Metadata by ID"]
# note: the content enum variables must have a distinct name or else the get overwritten in memory from initialization when requests are made
@router.get("/{track}", tags=tags, response_model=Union[FILERTrackBriefResponse, FILERTrackResponse],
    name="Get track metadata",
    description="retrieve track metadata for the FILER record identified by the `track` specified in the path; use `content=summary` for a brief response")
async def get_track_metadata(
        track = Depends(path_track_id),
        content: str = Query(ResponseContent.SUMMARY, description=f'response content; one of: {print_enum_values(METADATA_CONTENT_ENUM)}'),
        internal: InternalRequestParameters = Depends()
        ) -> Union[FILERTrackBriefResponse, FILERTrackResponse]:
    
    rContent = validate_response_content(METADATA_CONTENT_ENUM, content)
    helper = FILERRouteHelper(
        internal,
        ResponseConfiguration(
            content=rContent,
            model = FILERTrackResponse if rContent == ResponseContent.FULL \
                else FILERTrackBriefResponse
        ),
        Parameters(track=track))
    
    return await helper.get_track_metadata()


tags = ["Record by ID", "NIAGADS Genome Browser Configuration"]
@router.get("/{track}/config/igvbrowser", tags=tags, 
    response_model=Union[GenomeBrowserConfigResponse, GenomeBrowserExtendedConfigResponse],
    name="Get track Genome Browser configuration",
    description="retrieve NIAGADS Genome Browser track configuration for the FILER `track` specified in the path")
async def get_track_browser_config(
        track = Depends(path_track_id),
        content: str = Query(ResponseContent.SUMMARY, description=f'response content; one of: {print_enum_values(METADATA_CONTENT_ENUM)}'),
        internal: InternalRequestParameters = Depends()) \
    -> Union[GenomeBrowserConfigResponse, GenomeBrowserExtendedConfigResponse]:
        
    rContent = validate_response_content(METADATA_CONTENT_ENUM, content)
    helper = FILERRouteHelper(
        internal,
        ResponseConfiguration(
            content=rContent,
            model=GenomeBrowserExtendedConfigResponse \
                if rContent == ResponseContent.FULL \
                else GenomeBrowserConfigResponse
        ),
        Parameters(track=track)
    )
    
    return await helper.get_track_metadata()


tags = ["Record by ID", "Track Data by ID"]
@router.get("/{track}/data", tags=tags, 
    name="Get track data", response_model=Union[BEDResponse, BaseResponseModel],
    description="retrieve functional genomics track data from FILER in the specified region; specify `content=counts` to just retrieve a count of the number of hits in the specified region")
async def get_track_data(
        track = Depends(path_track_id),
        span: str=Depends(span_param),
        format: str= Depends(format_param),
        content: str = Query(ResponseContent.FULL, description=f'response content; one of: {print_enum_values(TRACK_DATA_CONTENT_ENUM)}'),
        internal: InternalRequestParameters = Depends()
        ) -> Union[BEDResponse, BaseResponseModel]:
    
    rContent = validate_response_content(TRACK_DATA_CONTENT_ENUM, content)
    helper = FILERRouteHelper(
        internal,
        ResponseConfiguration(
            content=rContent,
            format=format,
            model=BEDResponse if rContent == ResponseContent.FULL \
                else BaseResponseModel
        ),
        Parameters(track=track, span=span)
    )

    return await helper.get_track_data()


