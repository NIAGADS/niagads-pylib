from fastapi import APIRouter, Depends, Path, Query, Request, status
from fastapi.responses import RedirectResponse
from typing import Annotated, List, Optional, Union
from sqlalchemy.ext.asyncio import AsyncSession

from api.dependencies.exceptions import RESPONSES
from api.dependencies.database import AsyncSession

from api.dependencies.param_validation import convert_str2list, clean
from api.dependencies.location_params import span_param
from api.dependencies.shared_params import ResponseType, format_param

from api.response_models import GenomeBrowserConfigResponse, GenomeBrowserExtendedConfigResponse, RequestDataModel, BEDResponse

from ..common.constants import ROUTE_TAGS
from ..common.services import MetadataQueryService, ApiWrapperService
from ..dependencies import ROUTE_SESSION_MANAGER, InternalRequestParameters
from ..common.helpers import get_track_metadata as __get_track_metadata, HelperParameters
from ..models.track_response_model import FILERTrackResponse, FILERTrackBriefResponse

TAGS = ROUTE_TAGS
router = APIRouter(
    prefix="/track",
    tags=TAGS,
    responses=RESPONSES
)

tags = TAGS + ["Record(s) by ID", "Track Metadata by ID"]
@router.get("/{track}", tags=tags, response_model=FILERTrackBriefResponse,
    name="Get brief track description",
    description="retrieve simple track description for the FILER record identified by the `track` specified in the path")
async def get_track_summary(
        track: Annotated[str, Path(description="FILER track identifier")],
        internal: InternalRequestParameters = Depends()
        ) -> FILERTrackBriefResponse:
    
    opts = HelperParameters(internal=internal, responseModel=FILERTrackBriefResponse, parameters={'track': track})
    return await __get_track_metadata(opts)


tags = TAGS + ["Record(s) by ID", "Track Metadata by ID"]
@router.get("/{track}/metadata", tags=tags, response_model=FILERTrackResponse,
    name="Get full track metadata",
    description="retrieve full metadata for the FILER record identified by the `track` specified in the path")
async def get_track_metadata(
        track: Annotated[str, Path(description="FILER track identifier")],
        internal: InternalRequestParameters = Depends()
        ) -> FILERTrackResponse:

    opts = HelperParameters(internal=internal, responseModel=FILERTrackResponse, parameters={'track': track})
    return await __get_track_metadata(opts)


tags = TAGS + ["NIAGADS Genome Browser Configuration"]
@router.get("/{track}/browser_config", tags=tags, 
    response_model=Union[GenomeBrowserConfigResponse, GenomeBrowserExtendedConfigResponse],
    name="Get track Genome Browser configuration",
    description="retrieve NIAGADS Genome Browser track configuration for the FILER `track` specified in the path")
async def get_track_browser_config(
        track: Annotated[str, Path(description="FILER track identifier")],
        inclMetadata: Optional[bool] = Query(default=False, description="include filterable track metadata for the track selector display"),
        internal: InternalRequestParameters = Depends()) \
    -> Union[GenomeBrowserConfigResponse, GenomeBrowserExtendedConfigResponse]:
        
    responseModel = GenomeBrowserExtendedConfigResponse if inclMetadata else GenomeBrowserConfigResponse
    opts = HelperParameters(internal=internal, responseModel=responseModel, parameters={'track': track})
    return await __get_track_metadata(opts)


tags = TAGS + ["Track Data by ID"]
@router.get("/{track}/data", tags=tags, 
    name="Get track data", response_model=BEDResponse,
    description="retrieve functional genomics track data from FILER in the specified region")
async def get_track_data(
        track: Annotated[str, Path(description="FILER track identifier")],
        span: str=Depends(span_param),
        internal: InternalRequestParameters = Depends()
        ) -> BEDResponse:
    
    await MetadataQueryService(internal.session).validate_tracks(convert_str2list(track))
    result = await ApiWrapperService().get_track_hits(clean(track), span)
    return BEDResponse(request=internal.requestData, response=result)


