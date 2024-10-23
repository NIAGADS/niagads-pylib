from fastapi import APIRouter, Depends, Path, Query, Request
from typing import Annotated, List, Optional
from sqlalchemy.ext.asyncio import AsyncSession
from collections import OrderedDict, ChainMap
from itertools import groupby
from operator import itemgetter

from api.dependencies.filter_params import ExpressionType, FilterParameter
from api.dependencies.param_validation import clean
from api.dependencies.location_params import assembly_param, span_param
from api.dependencies.exceptions import RESPONSES
from api.dependencies.shared_params import ExtendedOptionalParams, OptionalParams
from api.internal.constants import FILER_N_TRACK_LOOKUP_LIMIT

from ..constants import ROUTE_SESSION_MANAGER, TRACK_SEARCH_FILTER_FIELD_MAP, ROUTE_TAGS
from ..dependencies import MetadataQueryService, ApiWrapperService
from ..models import TrackPublic, TrackQueryPublic

def merge_track_lists(trackList1, trackList2):
    matched = groupby(sorted(trackList1 + trackList2, key=itemgetter('track_id')), itemgetter('track_id'))
    combinedLists = [dict(ChainMap(*g)) for k, g in matched]
    return combinedLists
    

TAGS = ROUTE_TAGS 
router = APIRouter(
    prefix="/query",
    tags=TAGS,
    responses=RESPONSES
)

tags = TAGS + ['Record(s) by Text Search'] + ['Track Metadata by Text Search']
filter_param = FilterParameter(TRACK_SEARCH_FILTER_FIELD_MAP, ExpressionType.TEXT)
@router.get("/tracks", tags=tags, response_model=List[TrackPublic],
    name="Track Metadata Text Search", 
    description="find functional genomics tracks using category filters or by a keyword search againts all text fields in the track metadata")
async def query_track_metadata(
        session: Annotated[AsyncSession, Depends(ROUTE_SESSION_MANAGER)],
        assembly = Depends(assembly_param), filter = Depends(filter_param), 
        keyword: Optional[str] = Query(default=None, description="search all text fields by keyword"),
        options: ExtendedOptionalParams = Depends()):
    if filter is None and keyword is None:
        raise ValueError('must specify either a `filter` and/or a `keyword` to search')
    return await MetadataQueryService(session).query_track_metadata(assembly, filter, keyword, options)


@router.get('/region/summary', tags=tags, response_model=List[TrackQueryPublic], include_in_schema=False,
            name="Get a data summary for Tracks meeting Search Criteria", 
            description="retrieve counts of hits/overlaps in a region of interest from all functional genomics tracks whose metadata meets the search or filter criteria")
async def query_track_data_summary(request: Request, requestId: str):
    pass

@router.get("/region", tags=tags, 
    name="Get Data from Tracks meeting Search Criteria", 
    description="retrieve data in a region of interest from all functional genomics tracks whose metadata meets the search or filter criteria")
async def query_track_data(
        request: Request,
        session: Annotated[AsyncSession, Depends(ROUTE_SESSION_MANAGER)],
        apiWrapperService: Annotated[ApiWrapperService, Depends(ApiWrapperService)],
        assembly = Depends(assembly_param), filter = Depends(filter_param), 
        keyword: Optional[str] = Query(default=None, description="search all text fields by keyword"),
        span: str=Depends(span_param),
        options: OptionalParams = Depends()):
    
    if filter is None and keyword is None:
        raise ValueError('must specify either a `filter` and/or a `keyword` to search')
    
    # get tracks that meet the filter criteria
    opts = ExtendedOptionalParams(idsOnly=False, countOnly=False, page=None, limit=None )
    matchingTracks = await MetadataQueryService(session).query_track_metadata(assembly, filter, keyword, opts)
    
    # get tracks with data in the region
    informativeTracks = apiWrapperService.get_informative_tracks(span, assembly)
    
    # filter for tracks that match the filter
    matchingTrackIds = [ t.track_id for t in matchingTracks] # Track object
    informativeTrackIds = [t['track_id'] for t in informativeTracks] # dict
    targetTrackIds = list(set(matchingTrackIds).intersection(informativeTrackIds))

    if options.countOnly:    
        result = merge_track_lists([t.serialize(expandObjects=True) for t in matchingTracks], informativeTracks)
        result = [TrackQueryPublic(**t) for t in result if t['track_id'] in targetTrackIds]
        # informativeTracks = OrderedDict(sorted(informativeTracks.items(), key = lambda item: item[1], reverse=True))

        # requestId = request.headers.get("X-Request-ID")
        # request.session[requestId + '_query_summary'] = result
        # TODO: redirect so we can correctly serialize and pass on to viz tools
        return result
    
    # do the actual data lookup
    tracks = targetTrackIds
    
    # here's were we would implement paging based on number of hits / tracks?
    ## apply limit after determining most informative tracks
    limit = options.limit
    options.limit = None
    
    message = None
    if len(tracks) > FILER_N_TRACK_LOOKUP_LIMIT:
        message = f'Your search resulted in `{len(tracks)}` tracks. Pagination not yet implemented. Limiting query against FILER repository to the first `{FILER_N_TRACK_LOOKUP_LIMIT}` tracks.'
        tracks = tracks[:FILER_N_TRACK_LOOKUP_LIMIT]
        
    result = apiWrapperService.get_track_hits(','.join(tracks), span)
    if message is not None:
        result.update({'message': message})
        
    return result


tags = TAGS + ["API Helper", "Data Summary"]
@router.get("/filter", tags=tags, 
    name="Helper: Allowable Filter Fields", 
    description="get list of allowable fields for filter-based searches of FILER track metadata")
async def get_track_filters():
    return {k: v['description'] for k, v in TRACK_SEARCH_FILTER_FIELD_MAP.items()}

@router.get("/filter/{field}", tags=tags, 
    name="Helper: Filter Field Values", 
    description="get list of values and (optionally) associated FILER track counts for each allowable filter field")
async def get_track_filter_summary(session: Annotated[AsyncSession, Depends(ROUTE_SESSION_MANAGER)],
        field: str=Path(enum=list(TRACK_SEARCH_FILTER_FIELD_MAP.keys()),
        description="filter field; please note that there are too many possible values for `biosample`; the returned result summarizes over broad `tissue categories` only"),
        inclCounts: Optional[bool] = Query(default=False, description="include number of tracks meeting each field value")):
    return await MetadataQueryService(session).get_track_filter_summary(clean(field), inclCounts)

