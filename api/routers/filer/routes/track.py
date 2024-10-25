from fastapi import APIRouter, Depends, Path, Query, Request, status
from fastapi.responses import RedirectResponse
from typing import Annotated, List, Optional, Union
from sqlalchemy.ext.asyncio import AsyncSession
from starlette.datastructures import URL

from api.dependencies.database import AsyncSession
from api.dependencies.param_validation import convert_str2list, clean
from api.dependencies.location_params import span_param
from api.dependencies.exceptions import RESPONSES
from api.dependencies.shared_params import ResponseType, format_param
from api.response_models import GenomeBrowserConfigResponse, GenomeBrowserExtendedConfigResponse, RequestDataModel, BEDResponse

from ..constants import ROUTE_TAGS,ROUTE_SESSION_MANAGER
from ..dependencies import MetadataQueryService, ApiWrapperService
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
        session: Annotated[AsyncSession, Depends(ROUTE_SESSION_MANAGER)], 
        track: Annotated[str, Path(description="FILER track identifier")],
        requestData: RequestDataModel = Depends(RequestDataModel.from_request)
        ) -> FILERTrackBriefResponse:

    result = await MetadataQueryService(session).get_track_metadata(convert_str2list(track))
    return FILERTrackBriefResponse(request=requestData, response=result)

tags = TAGS + ["Record(s) by ID", "Track Metadata by ID"]
@router.get("/{track}/metadata", tags=tags, response_model=FILERTrackResponse,
    name="Get full track metadata",
    description="retrieve full metadata for the FILER record identified by the `track` specified in the path")
async def get_track_metadata(
        session: Annotated[AsyncSession, Depends(ROUTE_SESSION_MANAGER)], 
        track: Annotated[str, Path(description="FILER track identifier")],
        requestData: RequestDataModel = Depends(RequestDataModel.from_request)
        ) -> FILERTrackResponse:

    result = await MetadataQueryService(session).get_track_metadata(convert_str2list(track))
    return FILERTrackResponse(request=requestData, response=result)


tags = TAGS + ["NIAGADS Genome Browser Configuration"]
@router.get("/{track}/browser_config", tags=tags, 
    response_model=Union[GenomeBrowserConfigResponse, GenomeBrowserExtendedConfigResponse],
    name="Get track Genome Browser configuration",
    description="retrieve NIAGADS Genome Browser track configuration or session file for the functional genomics `track` specified in the path")
async def get_track_browser_config(
        session: Annotated[AsyncSession, Depends(ROUTE_SESSION_MANAGER)], 
        track: Annotated[str, Path(description="FILER track identifier")],
        inclMetadata: Optional[bool] = Query(default=False, description="include filterable track metadata for the track selector display"),
        requestData: RequestDataModel = Depends(RequestDataModel.from_request)) \
    -> Union[GenomeBrowserConfigResponse, GenomeBrowserExtendedConfigResponse]:
        
    result = await MetadataQueryService(session).get_track_metadata(convert_str2list(track))
    
    if inclMetadata:
        return GenomeBrowserExtendedConfigResponse(request=requestData, response=result)
    
    return GenomeBrowserConfigResponse(request=requestData, response=result)



tags = TAGS + ["Track Data by ID"]
@router.get("/{track}/data", tags=tags, 
    name="Get track data", response_model=BEDResponse,
    description="retrieve functional genomics track data from FILER in the specified region")
async def get_track_data(session: Annotated[AsyncSession, Depends(ROUTE_SESSION_MANAGER)], 
        track: Annotated[str, Path(description="FILER track identifier")],
        span: str=Depends(span_param),
        requestData: RequestDataModel = Depends(RequestDataModel.from_request)) -> BEDResponse:
    
    await MetadataQueryService(session).validate_tracks(convert_str2list(track))
    result = await ApiWrapperService().get_track_hits(clean(track), span)
    return BEDResponse(request=requestData, response=result)


