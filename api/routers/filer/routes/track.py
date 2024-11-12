from fastapi import APIRouter, Depends, Path, Query
from typing import Optional, Union

from api.common.enums import ResponseContent, ResponseFormat
from api.common.exceptions import RESPONSES
from api.common.formatters import print_enum_values
from api.dependencies.parameters.location import span_param
from api.dependencies.parameters.optional import format_param, get_response_content, get_response_format, validate_response_content
from api.common.helpers import Parameters

from api.response_models import GenomeBrowserConfigResponse, GenomeBrowserExtendedConfigResponse, BEDResponse
from api.response_models.base_models import BaseResponseModel

from ..common.constants import ROUTE_TAGS
from ..dependencies import InternalRequestParameters, path_track_id
from ..common.helpers import (get_track_metadata as __get_track_metadata, 
    get_track_data as __get_track_data, HelperParameters)
from ..models.track_response_model import FILERTrackResponse, FILERTrackBriefResponse

# TAGS = ROUTE_TAGS
router = APIRouter(
    prefix="/track",
#     tags=TAGS,
    responses=RESPONSES
)


tags = ["Record by ID", "Track Metadata by ID"]
# note: the content enum variables must have a distinct name or else the get overwritten in memory from initialization when requests are made
get_track_metadata_content_enum = get_response_content(exclude=[ResponseContent.IDS, ResponseContent.COUNTS])
@router.get("/{track}", tags=tags, response_model=Union[FILERTrackBriefResponse, FILERTrackResponse],
    name="Get track metadata",
    description="retrieve track metadata for the FILER record identified by the `track` specified in the path; use `content=summary` for a brief response")
async def get_track_metadata(
        track = Depends(path_track_id),
        content: str = Query(ResponseContent.SUMMARY, description=f'response content; one of: {print_enum_values(get_track_metadata_content_enum)}'),
        internal: InternalRequestParameters = Depends()
        ) -> Union[FILERTrackBriefResponse, FILERTrackResponse]:
    
    content = await validate_response_content(get_track_metadata_content_enum, content)
    responseModel = FILERTrackResponse if content == ResponseContent.FULL else FILERTrackBriefResponse
    opts = HelperParameters(internal=internal, 
        model=responseModel, content=content,
        parameters=Parameters(track=track))
    return await __get_track_metadata(opts)


tags = ["Record by ID", "NIAGADS Genome Browser Configuration"]
@router.get("/{track}/browser_config", tags=tags, 
    response_model=Union[GenomeBrowserConfigResponse, GenomeBrowserExtendedConfigResponse],
    name="Get track Genome Browser configuration",
    description="retrieve NIAGADS Genome Browser track configuration for the FILER `track` specified in the path")
async def get_track_browser_config(
        track = Depends(path_track_id),
        inclMetadata: Optional[bool] = Query(default=False, description="include filterable track metadata for the track selector display"),
        internal: InternalRequestParameters = Depends()) \
    -> Union[GenomeBrowserConfigResponse, GenomeBrowserExtendedConfigResponse]:
        
    responseModel = GenomeBrowserExtendedConfigResponse if inclMetadata \
        else GenomeBrowserConfigResponse
    opts = HelperParameters(internal=internal, model=responseModel, parameters=Parameters(track=track))
    return await __get_track_metadata(opts)


tags = ["Record by ID", "Track Data by ID"]

get_track_data_content_enum = get_response_content(exclude=[ResponseContent.IDS, ResponseContent.SUMMARY])
@router.get("/{track}/data", tags=tags, 
    name="Get track data", response_model=Union[BEDResponse, BaseResponseModel],
    description="retrieve functional genomics track data from FILER in the specified region; specify `content=counts` to just retrieve a count of the number of hits in the specified region")
async def get_track_data(
        track = Depends(path_track_id),
        span: str=Depends(span_param),
        format: str= Depends(format_param),
        content: str = Query(ResponseContent.FULL, description=f'response content; one of: {print_enum_values(get_track_data_content_enum)}'),
        internal: InternalRequestParameters = Depends()
        ) -> Union[BEDResponse, BaseResponseModel]:
    
    content = await validate_response_content(get_track_data_content_enum, content)
    responseModel = BEDResponse if content == ResponseContent.FULL else BaseResponseModel
    opts = HelperParameters(internal=internal, format=format, 
        model=responseModel, content=content,
        parameters=Parameters(track=track, span=span))
    return await __get_track_data(opts)


