from fastapi import APIRouter, Depends, Query
from typing import Union

from api.common.enums import ResponseContent
from api.common.exceptions import RESPONSES
from api.common.formatters import print_enum_values
from api.common.helpers import Parameters, ResponseConfiguration

from api.dependencies.parameters.location import span_param
from api.dependencies.parameters.optional import format_param, validate_response_content
from api.models.base_response_models import BaseResponseModel


from ..dependencies.parameters import InternalRequestParameters, path_track_id
from ..common.helpers import FILERRouteHelper
from ..common.enums import METADATA_CONTENT_ENUM, TRACK_DATA_CONTENT_ENUM
from ..models.filer_track import FILERTrackResponse, FILERTrackBriefResponse
from ..models.bed_features import BEDResponse


router = APIRouter(prefix="/track", responses=RESPONSES)

tags = ["Record by ID", "Track Metadata by ID"]
responseModels = Union[FILERTrackBriefResponse, FILERTrackResponse, BaseResponseModel]
@router.get("/{track}", tags=tags, response_model=responseModels,
    name="Get track metadata",
    description="retrieve track metadata for the FILER record identified by the `track` specified in the path; use `content=summary` for a brief response")
async def get_track_metadata(
        track = Depends(path_track_id),
        content: str = Query(ResponseContent.SUMMARY, description=f'response content; one of: {print_enum_values(METADATA_CONTENT_ENUM)}'),
        internal: InternalRequestParameters = Depends()
        ) -> responseModels:
    
    rContent = validate_response_content(METADATA_CONTENT_ENUM, content)
    helper = FILERRouteHelper(
        internal,
        ResponseConfiguration(
            content=rContent,
            model = FILERTrackResponse if rContent == ResponseContent.FULL \
                else FILERTrackBriefResponse if rContent == ResponseContent.SUMMARY \
                    else BaseResponseModel
        ),
        Parameters(track=track))
    
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


