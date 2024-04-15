from fastapi import APIRouter
from typing import Union

from ...dependencies import RESPONSES
from .dependencies import ROUTE_TAGS

TAGS = ROUTE_TAGS +  ["Track Metadata"]

router = APIRouter(
    prefix="/search",
    tags=TAGS,
    responses=RESPONSES
)

@router.get("/", tags=TAGS, 
            description="get metadata for all FILER tracks or those that meet the filter criteria")
async def search_track_metadata():
    return {"tracks": "TODO: retrieve tracks by filter"}

@router.get("/datasource/{datasource}", tags=TAGS, 
            name="Search for tracks by original data source", 
            description="get metadata for all FILER tracks by datasource")
async def datasource_search_track_metadata():
    return {"tracks": "TODO: retrieve tracks by filter"}

@router.get("/keyword/{keyword}", tags=TAGS, 
            name="Search track metadata by keyword", 
            description="search all FILER track metadata fields by keyword (exact, case-insensitive match)")
async def keyword_search_track_metadata():
    return {"tracks": "TODO: retrieve tracks by keyword"}

