from fastapi import APIRouter, Depends
from typing import Union

from ...dependencies import RESPONSES, assembly_param
from .dependencies import ROUTE_ABBREVIATION, ROUTE_NAME, ROUTE_TAGS, ROUTE_PREFIX
from .metadata import router as metadata

# for defining re-used query params, e.g., the filters https://stackoverflow.com/a/64366434

router = APIRouter(
    prefix=ROUTE_PREFIX,
    tags=ROUTE_TAGS,
    responses=RESPONSES,
    # dependencies=[Depends(assembly)]
)

@router.get("/", tags=ROUTE_TAGS, name="about", description="about the " + ROUTE_NAME)
async def read_root():
    return {"database": "FILER"}

@router.get("/query/", tags=ROUTE_TAGS, description="query data from FILER")
async def query(assembly = Depends(assembly_param), filter: Union[str, None] = None):
    return {"filter": filter, "assembly": assembly, "metadata": "TODO"}

@router.get("/query/{track}", tags=ROUTE_TAGS, description="query data from a specific FILER track")
async def query_track(track: str):
    return {"track": "track", "metadata": "TODO"}

router.include_router(metadata)