from fastapi import APIRouter, Depends, Path, Query
from typing import Annotated, Optional
from sqlalchemy.ext.asyncio import AsyncSession

from api.dependencies.database import AsyncSession
from api.dependencies.filter_params import ExpressionType, FilterParameter
from api.dependencies.param_validation import convert_str2list, clean
from api.dependencies.location_params import assembly_param, span_param
from api.dependencies.exceptions import RESPONSES
from api.dependencies.shared_params import OptionalParams

from .dependencies import ROUTE_TAGS,ROUTE_SESSION_MANAGER, MetadataQueryService, ApiWrapperService
from .model import Track

TAGS = ROUTE_TAGS
router = APIRouter(
    prefix="/track",
    tags=TAGS,
    responses=RESPONSES
)

tags = TAGS + ["Record(s) by ID", "Track Metadata by ID"]
@router.get("/record/{track}", tags=tags, 
    name="Get track metadata",
    description="retrieve metadata for the functional genomics `track` specified in the path")
async def get_track_metadata(
        session: Annotated[AsyncSession, Depends(ROUTE_SESSION_MANAGER)], 
        track: Annotated[str, Path(description="FILER track identifier")]):
    return await MetadataQueryService(session).get_track_metadata(convert_str2list(track))

@router.get("/record", tags=tags, 
    name="Get metadata for multiple tracks",
    description="retrieve metadata for one or more functional genomics tracks from FILER")
async def get_track_metadata(
        session: Annotated[AsyncSession, Depends(ROUTE_SESSION_MANAGER)], 
        track: Annotated[str, Query(description="comma separated list of one or more FILER track identifiers")]) -> Track:
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
async def get_track_data(session: Annotated[AsyncSession, Depends(ROUTE_SESSION_MANAGER)], 
        apiWrapperService: Annotated[ApiWrapperService, Depends(ApiWrapperService)],
        track: Annotated[str, Query(description="comma separated list of one or more FILER track identifiers")],
        span: str=Depends(span_param)):

    assembly = await MetadataQueryService(session).get_genome_build(convert_str2list(track), validate=True)
    if isinstance(assembly, dict):
        raise ValueError(f'Tracks map to multiple assemblies; please query GRCh37 and GRCh38 data independently')
        # TODO: return assembly -> track mapping in error message and/or suggest endpoint to query to get the mapping
        
    return apiWrapperService.get_track_hits(clean(track), span)