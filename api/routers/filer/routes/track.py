from fastapi import APIRouter, Depends, Path, Query
from typing import Annotated, Optional, Union

from api.common.exceptions import RESPONSES
from api.dependencies.parameters.location import span_param
from api.dependencies.parameters.optional import counts_only_param, format_param
from api.common.helpers import Parameters

from api.response_models import GenomeBrowserConfigResponse, GenomeBrowserExtendedConfigResponse, BEDResponse
from api.response_models.base_models import BaseResponseModel

from ..common.constants import ROUTE_TAGS
from ..dependencies import InternalRequestParameters, path_track_id
from ..common.helpers import (get_track_metadata as __get_track_metadata, 
    get_track_data as __get_track_data, HelperParameters)
from ..models.track_response_model import FILERTrackResponse, FILERTrackBriefResponse

TAGS = ROUTE_TAGS
router = APIRouter(
    prefix="/track",
    tags=TAGS,
    responses=RESPONSES
)

tags = TAGS + ["Record by ID", "Track Metadata by ID"]
@router.get("/{track}", tags=tags, response_model=FILERTrackBriefResponse,
    name="Get brief track description",
    description="retrieve simple track description for the FILER record identified by the `track` specified in the path")
async def get_track_summary(
        track = Depends(path_track_id),
        internal: InternalRequestParameters = Depends()
        ) -> FILERTrackBriefResponse:
    
    opts = HelperParameters(internal=internal, model=FILERTrackBriefResponse, parameters=Parameters(track=track))
    return await __get_track_metadata(opts)


tags = TAGS + ["Record by ID", "Track Metadata by ID"]
@router.get("/{track}/metadata", tags=tags, response_model=FILERTrackResponse,
    name="Get full track metadata",
    description="retrieve full metadata for the FILER record identified by the `track` specified in the path")
async def get_track_metadata(
        track = Depends(path_track_id),
        internal: InternalRequestParameters = Depends()
        ) -> FILERTrackResponse:

    opts = HelperParameters(internal=internal, model=FILERTrackResponse, parameters=Parameters(track=track))
    return await __get_track_metadata(opts)


tags = TAGS + ["Record by ID", "NIAGADS Genome Browser Configuration"]
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


tags = TAGS + ["Record by ID", "Track Data by ID"]
@router.get("/{track}/data", tags=tags, 
    name="Get track data", response_model=Union[BEDResponse, BaseResponseModel],
    description="retrieve functional genomics track data from FILER in the specified region; specify `countsOnly` to just retrieve a count of the number of hits in the specified region")
async def get_track_data(
        track = Depends(path_track_id),
        span: str=Depends(span_param),
        format: str= Depends(format_param),
        countsOnly: Optional[bool]=Depends(counts_only_param),
        internal: InternalRequestParameters = Depends()
        ) -> Union[BEDResponse, BaseResponseModel]:
    
    responseModel = BaseResponseModel if countsOnly else BEDResponse
    opts = HelperParameters(internal=internal, format=format, model=responseModel, 
        parameters=Parameters(track=track, span=span, countsOnly=countsOnly))
    return await __get_track_data(opts)


