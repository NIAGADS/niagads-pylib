from fastapi import APIRouter, Depends, Query
from typing import Annotated, Optional, Union

from api.dependencies.exceptions import RESPONSES
from api.dependencies.parameters.location import span_param
from api.dependencies.parameters.optional import format_param
from api.response_models import GenomeBrowserConfigResponse, GenomeBrowserExtendedConfigResponse
from api.common.helpers import Parameters

from ..common.helpers import HelperParameters, get_track_metadata as __get_track_metadata
from ..common.constants import ROUTE_TAGS
from ..models.track_response_model import FILERTrackResponse
from ..dependencies import InternalRequestParameters

TAGS = ROUTE_TAGS
router = APIRouter(
    prefix="/metadata",
    tags=TAGS,
    responses=RESPONSES
)

tags = TAGS + ["Track Metadata by ID"]
@router.get("/", tags=tags, response_model=FILERTrackResponse,
    name="Get metadata for multiple tracks",
    description="retrieve full metadata for one or more FILER track records")
async def get_track_metadata(
        track: Annotated[str, Query(description="comma separated list of one or more FILER track identifiers")],
        format: str= Depends(format_param),
        internal: InternalRequestParameters = Depends()) -> FILERTrackResponse:
    
    opts = HelperParameters(internal=internal, format=format, model=FILERTrackResponse, parameters=Parameters(track=track))
    return await __get_track_metadata(opts)


tags = TAGS + ["NIAGADS Genome Browser Configuration"]
@router.get("/browser_config", tags=tags,  response_model=Union[GenomeBrowserConfigResponse, GenomeBrowserExtendedConfigResponse],
    name="Get Genome Browser configuration for multiple tracks",
    description="retrieve NIAGADS Genome Browser track configuration for one or more FILER `track`(s) specified in the path")
async def get_track_browser_config(
        track: Annotated[str, Query(description="comma separated list of one or more FILER track identifiers")],
        inclMetadata: Optional[bool] = Query(default=False, description="include filterable track metadata for the track selector display"),
        format: str= Depends(format_param),
        internal: InternalRequestParameters = Depends()
        ) -> Union[GenomeBrowserConfigResponse, GenomeBrowserExtendedConfigResponse]:

    responseModel = GenomeBrowserExtendedConfigResponse if inclMetadata \
        else GenomeBrowserConfigResponse
    opts = HelperParameters(internal=internal, format=format, model=responseModel, parameters=Parameters(track=track))
    return await __get_track_metadata(opts)
