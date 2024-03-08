from fastapi import APIRouter
from typing import Union

from ...dependencies import RESPONSES
from .dependencies import ROUTE_TAGS

TAGS = ROUTE_TAGS +  ["Track Metadata"]

router = APIRouter(
    prefix="/metadata",
    tags=TAGS,
    responses=RESPONSES
)

@router.get("/query", tags=TAGS, description="get metadata for all FILER tracks or those that meet the filter criteria")
async def query_track_metadata():
    return {"tracks": "TODO: retrieve all tracks"}

@router.get("/{track}", tags=TAGS, description="get metadata for a specific FILER track")
async def track_metadata_by_id(track: str):
    return {"track": track, "metadata": "TODO"}


