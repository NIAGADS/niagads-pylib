from fastapi import APIRouter
from typing import Union

tags = ["FILER", "Track Metadata"]

router = APIRouter(
    prefix="/metadata",
    tags=tags,
    responses={404: {"description": "Not found"}},
)

@router.get("/query", tags=tags, description="get metadata for all FILER tracks or those that meet the filter criteria")
async def query_track_metadata():
    return {"tracks": "TODO: retrieve all tracks"}


@router.get("/{track_id}", tags=tags)
async def track_metadata_by_id(track_id: str, description="get metadata for a specific FILER track"):
    return {"track": track_id, "metadata": "TODO"}

