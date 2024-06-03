from fastapi import APIRouter, Depends
from typing import Union, Annotated

from api.dependencies.location_params import assembly_param, chromosome_param
from api.dependencies.exceptions import RESPONSES

from .dependencies import ROUTE_TAGS
from .model import Track

TAGS = ROUTE_TAGS +  ["Data Retrieval", "Find Data Tracks"]

router = APIRouter(
    prefix="/track",
    tags=TAGS,
    responses=RESPONSES
)

@router.get("/search", tags=TAGS, 
            name="Search for functional genomics tracks", 
            description="get metadata for all FILER tracks by datasource")
async def find_tracks():
    return {"tracks": "TODO: retrieve tracks by filter"}

# query(assembly = Depends(assembly_param), chromosome = Depends(chromosome_param), filter: Union[str, None] = None):


@router.get("/", tags=ROUTE_TAGS, description="retrieve data from one or more FILER tracks by identifier")
async def query(assembly = Depends(assembly_param), chromosome = Depends(chromosome_param), filter: Union[str, None] = None):
    return {"filter": filter, "assembly": assembly, "chromosome": chromosome, "metadata": "TODO"}

@router.get("/report/{track_id}", tags=ROUTE_TAGS, description="retrieve meta-data describing FILER data track specified by {track_id}")
async def query_track(track: str):
    return {"track": track, "result": []}


