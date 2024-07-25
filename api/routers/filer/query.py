from fastapi import APIRouter, Depends, Path, Query
from typing import Annotated, Optional

from api.dependencies.filter_params import ExpressionType, FilterParameter
from api.dependencies.param_validation import clean
from api.dependencies.location_params import assembly_param
from api.dependencies.exceptions import RESPONSES
from api.dependencies.shared_params import OptionalParams

from .dependencies import ROUTE_TAGS, CacheQueryService as Service, ApiWrapperService, TRACK_SEARCH_FILTER_FIELD_MAP

TAGS = ROUTE_TAGS

router = APIRouter(
    prefix="/query",
    tags=TAGS,
    responses=RESPONSES
)

tags = TAGS + ['Records by Text Search']
filter_param = FilterParameter(TRACK_SEARCH_FILTER_FIELD_MAP, ExpressionType.TEXT)
@router.get("/", tags=tags, 
    name="Track Metadata Text Search", 
    description="find FILER tracks by querying against the track metadata using category filters or by a keyword search againts all text fields")
async def query_track_metadata(service: Annotated[Service, Depends(Service)],
    assembly = Depends(assembly_param), filter = Depends(filter_param), 
    keyword: Optional[str] = Query(default=None, description="search all text fields by keyword"),
    options: OptionalParams = Depends(),
    ):
    if filter is None and keyword is None:
        raise ValueError('must specify either a `filter` and/or a `keyword` to search')
    return service.query_track_metadata(assembly, filter, keyword, options)


tags = TAGS +  ["API Helper", "Data Summary"]
@router.get("/filter", tags=tags, 
    name="Helper: Allowable Filter Fields", 
    description="get list of allowable fields for filter-based searches of FILER track metadata")
async def get_track_filters():
    return {k: v['description'] for k, v in TRACK_SEARCH_FILTER_FIELD_MAP.items()}

@router.get("/filter/{field}", tags=tags, 
    name="Helper: Filter Field Values", 
    description="get list of values and associated FILER track counts for each allowable filter field")
async def get_track_filter_summary(service: Annotated[Service, Depends(Service)], 
    field: str=Path(enum=list(TRACK_SEARCH_FILTER_FIELD_MAP.keys()),
        description="filter field; please note that there are too many possible values for `biosample`; the returned result summarizes over broad `tissue categories` only")
):
    return service.get_track_filter_summary(clean(field))