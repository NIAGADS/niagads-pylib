from fastapi import APIRouter, Depends
from typing import Union, Annotated

from ...dependencies import RESPONSES, assembly_param, chromosome_param
from .dependencies import ROUTE_TAGS

TAGS = ROUTE_TAGS +  ["Data Retrieval"]

router = APIRouter(
    prefix="/query",
    tags=TAGS,
    responses=RESPONSES
)

@router.get("/", tags=ROUTE_TAGS, description="query data from FILER")
async def query(assembly = Depends(assembly_param), chromosome = Depends(chromosome_param), filter: Union[str, None] = None):
    return {"filter": filter, "assembly": assembly, "chromosome": chromosome, "metadata": "TODO"}

@router.get("/{track}", tags=ROUTE_TAGS, description="query data from a specific FILER track")
async def query_track(track: str):
    return {"track": "track", "metadata": "TODO"}

