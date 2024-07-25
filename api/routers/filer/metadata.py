from fastapi import APIRouter, Depends, Query
from typing import Union, Annotated

from api.dependencies.filter_params import ExpressionType, FilterParameter
from api.dependencies.param_validation import clean
from api.dependencies.location_params import assembly_param, chromosome_param
from api.dependencies.exceptions import RESPONSES
from api.dependencies.shared_params import OptionalParams

from .dependencies import ROUTE_TAGS, Service, TRACK_SEARCH_FILTER_FIELD_MAP
from .model import Track

TAGS = ROUTE_TAGS +  ["Metadata Retrieval"]

router = APIRouter(
    prefix="/metadata",
    tags=TAGS,
    responses=RESPONSES
)


@router.get("/", tags=ROUTE_TAGS, 
    name="Lookup functional genomics track metadata from FILER",
    description="retrieve metadata for (one or more) FILER track(s) by identifier")
async def get_track_metadata(service: Annotated[Service, Depends(Service)], 
    track: Annotated[str, Query(description="comma separated list of one or more FILER track identifiers")]):
    return service.get_track_metadata(clean(track)) # FIXME: .clean()



filter_param = FilterParameter(TRACK_SEARCH_FILTER_FIELD_MAP, ExpressionType.TEXT)
@router.get("/search", tags=TAGS + ['Find Data Tracks'], 
    name="Search for functional genomics tracks in the FILER repository", 
    description="find FILER tracks by querying against the track metadata")
async def search_track_metadata(service: Annotated[Service, Depends(Service)],
    assembly = Depends(assembly_param), filter = Depends(filter_param),
    options: OptionalParams = Depends()):
    return service.query_track_metadata(assembly, filter, options)



