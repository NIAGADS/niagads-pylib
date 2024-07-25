from fastapi import APIRouter, Depends, Query
from typing import Annotated, Optional

from api.dependencies.filter_params import ExpressionType, FilterParameter
from api.dependencies.param_validation import clean
from api.dependencies.location_params import assembly_param
from api.dependencies.exceptions import RESPONSES
from api.dependencies.shared_params import OptionalParams

from .dependencies import ROUTE_TAGS, CacheQueryService as Service, TRACK_SEARCH_FILTER_FIELD_MAP

TAGS = ROUTE_TAGS +  ["Metadata Retrieval"]

router = APIRouter(
    prefix="/metadata",
    tags=TAGS,
    responses=RESPONSES
)


@router.get("/", tags=ROUTE_TAGS, 
    name="Lookup functional genomics track metadata from FILER",
    description="retrieve metadata for (one or more) track(s) by identifier")
async def get_track_metadata(service: Annotated[Service, Depends(Service)], 
    track: Annotated[str, Query(description="comma separated list of one or more FILER track identifiers")]):
    return service.get_track_metadata(clean(track)) # FIXME: .clean()


filter_param = FilterParameter(TRACK_SEARCH_FILTER_FIELD_MAP, ExpressionType.TEXT)
@router.get("/search", tags=TAGS + ['Find Data Tracks'], 
    name="Search for tracks using category filters or by keyword", 
    description="find FILER tracks by querying against the track metadata")
async def search_track_metadata(service: Annotated[Service, Depends(Service)],
    assembly = Depends(assembly_param), filter = Depends(filter_param), 
    keyword: Optional[str] = Query(default=None, description="search all text fields by keyword"),
    options: OptionalParams = Depends(),
    ):
    if filter is None and keyword is None:
        raise ValueError('must specify either a `filter` and/or a `keyword` to search')
    return service.query_track_metadata(assembly, filter, keyword, options)



