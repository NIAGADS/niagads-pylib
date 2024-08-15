from fastapi import APIRouter, Depends, Path, Query
from typing import Annotated, Optional

from api.dependencies.filter_params import ExpressionType, FilterParameter
from api.dependencies.param_validation import clean
from api.dependencies.location_params import assembly_param, span_param
from api.dependencies.exceptions import RESPONSES
from api.dependencies.shared_params import OptionalParams

from .dependencies import ROUTE_TAGS, CacheQueryService, ApiWrapperService, TRACK_SEARCH_FILTER_FIELD_MAP

TAGS = ROUTE_TAGS
router = APIRouter(
    prefix="/track",
    tags=TAGS,
    responses=RESPONSES
)

def __validate_track(track: str, service: CacheQueryService):
    tracks = clean(track).split(',')
    service.validate_tracks(tracks)
    return tracks


tags = TAGS + ["Record(s) by ID", "Track Metadata by ID"]
@router.get("/record/{track}", tags=tags, 
    name="Get track metadata",
    description="retrieve metadata for the functional genomics `track` specified in the path")
async def get_track_metadata(service: Annotated[CacheQueryService, Depends(CacheQueryService)], 
    track: Annotated[str, Path(description="FILER track identifier")]):
    return service.get_track_metadata(__validate_track(track, service)) # b/c its been cleaned

@router.get("/record", tags=tags, 
    name="Get metadata for multiple tracks",
    description="retrieve metadata for one or more functional genomics tracks from FILER")
async def get_track_metadata(service: Annotated[CacheQueryService, Depends(CacheQueryService)], 
    track: Annotated[str, Query(description="comma separated list of one or more FILER track identifiers")]):
    return service.get_track_metadata(__validate_track(track, service)) # b/c its been cleaned


tags = TAGS + ["Track Data by ID"]
@router.get("/data/{track}", tags=tags, 
    name="Get track data",
    description="retrieve functional genomics track data from FILER in the specified region")
async def get_track_data(cacheService: Annotated[CacheQueryService, Depends(CacheQueryService)], 
    apiWrapperService: Annotated[ApiWrapperService, Depends(ApiWrapperService)],
    track: Annotated[str, Path(description="FILER track identifier")],
    span: str=Depends(span_param)):

    __validate_track(track, cacheService)
    return apiWrapperService.get_track_hits(clean(track), span)


@router.get("/data", tags=tags, 
    name="Get data from multiple tracks",
    description="retrieve data from one or more functional genomics tracks from FILER in the specified region")
async def get_track_data(cacheService: Annotated[CacheQueryService, Depends(CacheQueryService)], 
    apiWrapperService: Annotated[ApiWrapperService, Depends(ApiWrapperService)],
    track: Annotated[str, Query(description="comma separated list of one or more FILER track identifiers")],
    span: str=Depends(span_param)):

    tracks = __validate_track(track, cacheService)
    assembly = cacheService.get_genome_build(tracks)
    if isinstance(assembly, dict):
        raise ValueError(f'Tracks map to multiple assemblies; please query GRCh37 and GRCh38 data independently')
        # TODO: return assembly -> track mapping in error message and/or suggest endpoint to query to get the mapping
        
    return apiWrapperService.get_track_hits(clean(track), span)