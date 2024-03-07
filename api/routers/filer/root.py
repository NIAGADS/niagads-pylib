from fastapi import APIRouter
from typing import Union
from .metadata import router as metadata

# for defining re-used query params, e.g., the filters https://stackoverflow.com/a/64366434

fullResourceName = "FILER Functional Genomics Repository"
resourceAbbrev = "FILER"

tags = [resourceAbbrev]

router = APIRouter(
    prefix="/filer",
    tags=tags,
    responses={404: {"description": "Not found"}},
)

@router.get("/", tags=['FILER'], name="about", description="about the " + fullResourceName)
async def read_root():
    return {"database": "FILER"}

@router.get("/query/", tags=tags, description="query data from FILER")
async def query(filter: Union[str, None] = None):
    return {"filter": filter, "metadata": "TODO"}

@router.get("/query/{track}", tags=tags, description="query data from a specific FILER track")
async def query_track(track: str):
    return {"track": "track", "metadata": "TODO"}

router.include_router(metadata)