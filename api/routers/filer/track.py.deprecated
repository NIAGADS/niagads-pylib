from fastapi import APIRouter, Depends
from typing import Union, Annotated

from ...shared_dependencies import RESPONSES, assembly_param, chromosome_param
from .dependencies import ROUTE_TAGS

TAGS = ROUTE_TAGS +  ["Data Retrieval"]

router = APIRouter(
    prefix="/track",
    tags=TAGS,
    responses=RESPONSES
)

@router.get("/", tags=ROUTE_TAGS, description="retrieve data from one or more FILER tracks by identifier")
async def query(assembly = Depends(assembly_param), chromosome = Depends(chromosome_param), filter: Union[str, None] = None):
    return {"filter": filter, "assembly": assembly, "chromosome": chromosome, "metadata": "TODO"}

@router.get("/info", tags=ROUTE_TAGS, description="retrieve meta-data from one or more FILER tracks by identifier")
async def query_track(track: str):
    return {"track": track, "result": []}


