from fastapi import APIRouter, Depends, Path, Query, Request, status
from fastapi.responses import RedirectResponse
from fastapi.encoders import jsonable_encoder
from typing import Annotated, List
from sqlalchemy.ext.asyncio import AsyncSession

from api.dependencies.database import AsyncSession
from api.dependencies.param_validation import convert_str2list, clean
from api.dependencies.location_params import span_param
from api.dependencies.exceptions import RESPONSES
from api.dependencies.shared_params import OptionalParams, ResponseType, format_param
from api.response_models import BrowserTrack, VizTable, VizTableOptions

from ..dependencies import ROUTE_TAGS,ROUTE_SESSION_MANAGER, MetadataQueryService, ApiWrapperService
from ..models import TrackPublic

TAGS = ROUTE_TAGS
router = APIRouter(
    prefix="/track",
    tags=TAGS,
    responses=RESPONSES
)

tags = TAGS + ["Record(s) by ID", "Track Metadata by ID"]
@router.get("/record/{track}", tags=tags, response_model=List[TrackPublic],
    name="Get track metadata",
    description="retrieve metadata for the functional genomics `track` specified in the path")
async def get_track_metadata(
        session: Annotated[AsyncSession, Depends(ROUTE_SESSION_MANAGER)], 
        track: Annotated[str, Path(description="FILER track identifier")]):
    return await MetadataQueryService(session).get_track_metadata(convert_str2list(track))


@router.get("/record", tags=tags, response_model=List[TrackPublic],
    name="Get metadata for multiple tracks",
    description="retrieve metadata for one or more functional genomics tracks from FILER")
async def get_multi_track_metadata(
        request: Request,
        session: Annotated[AsyncSession, Depends(ROUTE_SESSION_MANAGER)], 
        track: Annotated[str, Query(description="comma separated list of one or more FILER track identifiers")],
        format: str= Depends(format_param)):
    response = await MetadataQueryService(session).get_track_metadata(convert_str2list(track)) # b/c its been cleaned
    
    if format == ResponseType.JSON:
        return response
    else:
        data = [ TrackPublic(**jsonable_encoder(t)).serialize(expandObjects=True) for t in response ]
        columns = TrackPublic.table_columns()
        columnIds = [c['id'] for c in columns]
        options = VizTableOptions(disableColumnFilters=True, defaultColumns=columnIds[:10])
        requestId = request.headers.get("X-Request-ID")
        request.session[requestId + '_table'] = VizTable(id='tracks', data=data, columns=columns, options=options).serialize()
        redirectUrl = f'/api/view/table?requestId={requestId}&field=table'
        return RedirectResponse(url=redirectUrl, status_code=status.HTTP_303_SEE_OTHER)
    

tags = TAGS + ["NIAGADS Genome Browser Configuration"]
@router.get("/browser/{track}", tags=tags, response_model=List[BrowserTrack],
    name="Get track Genome Browser configuration",
    description="retrieve NIAGADS Genome Browser track configuration or session file for the functional genomics `track` specified in the path")
async def get_track_browser_config(
        session: Annotated[AsyncSession, Depends(ROUTE_SESSION_MANAGER)], 
        track: Annotated[str, Path(description="FILER track identifier")]):
    return await MetadataQueryService(session).get_track_metadata(convert_str2list(track))


@router.get("/browser", tags=tags,  response_model=List[BrowserTrack],
    name="Get Genome Browser configuration for multiple tracks",
    description="retrieve NIAGADS Genome Browser track configuration of session file for one or more functional genomics tracks from FILER")
async def get_multi_track_browser_config(
        session: Annotated[AsyncSession, Depends(ROUTE_SESSION_MANAGER)], 
        track: Annotated[str, Query(description="comma separated list of one or more FILER track identifiers")]):
    return await MetadataQueryService(session).get_track_metadata(convert_str2list(track)) # b/c its been cleaned


tags = TAGS + ["Track Data by ID"]
@router.get("/data/{track}", tags=tags, 
    name="Get track data",
    description="retrieve functional genomics track data from FILER in the specified region")
async def get_track_data(session: Annotated[AsyncSession, Depends(ROUTE_SESSION_MANAGER)], 
        apiWrapperService: Annotated[ApiWrapperService, Depends(ApiWrapperService)],
        track: Annotated[str, Path(description="FILER track identifier")],
        span: str=Depends(span_param)):
    
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