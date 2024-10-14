from fastapi import APIRouter, Depends, Path, Query
from typing import Annotated, Optional
from sqlalchemy.ext.asyncio import AsyncSession

from api.dependencies.database import DatabaseSessionManager
from api.dependencies.filter_params import ExpressionType, FilterParameter
from api.dependencies.param_validation import clean
from api.dependencies.location_params import assembly_param, span_param
from api.dependencies.exceptions import RESPONSES
from api.dependencies.shared_params import OptionalParams

from .dependencies import ROUTE_TAGS, MetadataQueryService, ApiWrapperService, ROUTE_SESSION_MANAGER, TRACK_SEARCH_FILTER_FIELD_MAP
from api.internal.constants import FILER_N_TRACK_LOOKUP_LIMIT

TAGS = ROUTE_TAGS 
router = APIRouter(
    prefix="/query",
    tags=TAGS,
    responses=RESPONSES
)

tags = TAGS + ['Record(s) by Text Search'] + ['Track Metadata by Text Search']
filter_param = FilterParameter(TRACK_SEARCH_FILTER_FIELD_MAP, ExpressionType.TEXT)
@router.get("/tracks", tags=tags, 
    name="Track Metadata Text Search", 
    description="find functional genomics tracks using category filters or by a keyword search againts all text fields in the track metadata")
async def query_track_metadata(session: Annotated[AsyncSession, Depends(ROUTE_SESSION_MANAGER)],
        assembly = Depends(assembly_param), filter = Depends(filter_param), 
        keyword: Optional[str] = Query(default=None, description="search all text fields by keyword"),
        options: OptionalParams = Depends()):
    if filter is None and keyword is None:
        raise ValueError('must specify either a `filter` and/or a `keyword` to search')
    return await MetadataQueryService(session).query_track_metadata(assembly, filter, keyword, options)


@router.get("/region", tags=tags, 
    name="Get Data from Tracks meeting Search Criteria", 
    description="retrieve data in a region of interest from all functional genomics tracks whose metadata meets the search or filter criteria")
async def query_track_data(session: Annotated[AsyncSession, Depends(ROUTE_SESSION_MANAGER)],
        apiWrapperService: Annotated[ApiWrapperService, Depends(ApiWrapperService)],
        assembly = Depends(assembly_param), filter = Depends(filter_param), 
        keyword: Optional[str] = Query(default=None, description="search all text fields by keyword"),
        span: str=Depends(span_param),
        options: OptionalParams = Depends()):
    if filter is None and keyword is None:
        raise ValueError('must specify either a `filter` and/or a `keyword` to search')
    
    options.idsOnly = True
    # temp to get accurate count; TODO: figure out when limit gets applied in this case
    limit = options.limit
    options.limit = None
    tracks = await MetadataQueryService(session).query_track_metadata(assembly, filter, keyword, options)
    
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

