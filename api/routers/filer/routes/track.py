from fastapi import APIRouter, Depends, Path, Query, Request, status
from fastapi.responses import RedirectResponse
from typing import Annotated, List
from sqlalchemy.ext.asyncio import AsyncSession
from starlette.datastructures import URL

from api.dependencies.database import AsyncSession
from api.dependencies.param_validation import convert_str2list, clean
from api.dependencies.location_params import span_param
from api.dependencies.exceptions import RESPONSES
from api.dependencies.shared_params import ResponseType, format_param
from api.response_models import GenomeBrowserConfigResponse, RequestDataModel

from ..constants import ROUTE_TAGS,ROUTE_SESSION_MANAGER
from ..dependencies import MetadataQueryService, ApiWrapperService
from ..models import TrackResponse, Track

TAGS = ROUTE_TAGS
router = APIRouter(
    prefix="/track",
    tags=TAGS,
    responses=RESPONSES
)

tags = TAGS + ["Record(s) by ID", "Track Metadata by ID"]
@router.get("/record/{track}", tags=tags, response_model=TrackResponse,
    name="Get track metadata",
    description="retrieve metadata for the functional genomics `track` specified in the path")
async def get_track_metadata(
        session: Annotated[AsyncSession, Depends(ROUTE_SESSION_MANAGER)], 
        track: Annotated[str, Path(description="FILER track identifier")],
        requestData: RequestDataModel = Depends(RequestDataModel.from_request)
        ) -> TrackResponse:

    result = await MetadataQueryService(session).get_track_metadata(convert_str2list(track))
    return TrackResponse(request=requestData, response=result)


@router.get("/record", tags=tags, response_model=TrackResponse,
    name="Get metadata for multiple tracks",
    description="retrieve metadata for one or more functional genomics tracks from FILER")
async def get_multi_track_metadata(
        request: Request,
        session: Annotated[AsyncSession, Depends(ROUTE_SESSION_MANAGER)], 
        track: Annotated[str, Query(description="comma separated list of one or more FILER track identifiers")],
        requestData: RequestDataModel = Depends(RequestDataModel.from_request),
        format: str= Depends(format_param)) -> TrackResponse:
    
    result: List[Track] = await MetadataQueryService(session).get_track_metadata(convert_str2list(track)) # b/c its been cleaned
    
    if format == ResponseType.JSON:
        return TrackResponse(request=requestData, response=result)
    else:
        request.session[requestData.request_id + '_response'] = [t.serialize(expandObjs=True, collapseUrls=True) for t in result]
        request.session[requestData.request_id + '_request'] = requestData.serialize()
        redirectUrl = f'/view/table/filer_track?forwardingRequestId={requestData.request_id}'
        return RedirectResponse(url=redirectUrl, status_code=status.HTTP_303_SEE_OTHER)
    

tags = TAGS + ["NIAGADS Genome Browser Configuration"]
@router.get("/browser/{track}", tags=tags, response_model=GenomeBrowserConfigResponse,
    name="Get track Genome Browser configuration",
    description="retrieve NIAGADS Genome Browser track configuration or session file for the functional genomics `track` specified in the path")
async def get_track_browser_config(
        session: Annotated[AsyncSession, Depends(ROUTE_SESSION_MANAGER)], 
        track: Annotated[str, Path(description="FILER track identifier")],
        requestData: RequestDataModel = Depends(RequestDataModel.from_request)) -> GenomeBrowserConfigResponse:
    result = await MetadataQueryService(session).get_track_metadata(convert_str2list(track))
    return GenomeBrowserConfigResponse(request=requestData, response=result)


@router.get("/browser", tags=tags,  response_model=GenomeBrowserConfigResponse,
    name="Get Genome Browser configuration for multiple tracks",
    description="retrieve NIAGADS Genome Browser track configuration of session file for one or more functional genomics tracks from FILER")
async def get_multi_track_browser_config(
        session: Annotated[AsyncSession, Depends(ROUTE_SESSION_MANAGER)], 
        track: Annotated[str, Query(description="comma separated list of one or more FILER track identifiers")],
        requestData: RequestDataModel = Depends(RequestDataModel.from_request)) -> GenomeBrowserConfigResponse:
    result = await MetadataQueryService(session).get_track_metadata(convert_str2list(track)) # b/c its been cleaned
    return GenomeBrowserConfigResponse(request=requestData, response=result)


tags = TAGS + ["Track Data by ID"]
@router.get("/data/{track}", tags=tags, 
    name="Get track data",
    description="retrieve functional genomics track data from FILER in the specified region")
async def get_track_data(session: Annotated[AsyncSession, Depends(ROUTE_SESSION_MANAGER)], 
        apiWrapperService: Annotated[ApiWrapperService, Depends(ApiWrapperService)],
        track: Annotated[str, Path(description="FILER track identifier")],
        span: str=Depends(span_param),
        requestData: RequestDataModel = Depends(RequestDataModel.from_request)):
    
    await MetadataQueryService(session).validate_tracks(convert_str2list(track))
    return apiWrapperService.get_track_hits(clean(track), span)


@router.get("/data", tags=tags,
    name="Get data from multiple tracks",
    description="retrieve data from one or more functional genomics tracks from FILER in the specified region")
async def get_multi_track_data(
        session: Annotated[AsyncSession, Depends(ROUTE_SESSION_MANAGER)], 
        apiWrapperService: Annotated[ApiWrapperService, Depends(ApiWrapperService)],
        track: Annotated[str, Query(description="comma separated list of one or more FILER track identifiers")],
        span: str=Depends(span_param)):

    assembly = await MetadataQueryService(session).get_genome_build(convert_str2list(track), validate=True)
    if isinstance(assembly, dict):
        raise ValueError(f'Tracks map to multiple assemblies; please query GRCh37 and GRCh38 data independently')
        # TODO: return assembly -> track mapping in error message and/or suggest endpoint to query to get the mapping
        
    return apiWrapperService.get_track_hits(clean(track), span)