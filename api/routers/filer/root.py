from fastapi import APIRouter, Depends
from typing import Union, Annotated

from ...internal.shared_dependencies import RESPONSES
from .dependencies import ROUTE_ABBREVIATION, ROUTE_NAME, ROUTE_TAGS, ROUTE_PREFIX
from ...internal.shared_dependencies import RESPONSES, assembly_param, chromosome_param, SharedParams

router = APIRouter(
    prefix=ROUTE_PREFIX,
    tags=ROUTE_TAGS,
    responses=RESPONSES,
    # dependencies=[Depends(assembly)] -- adds dependencies to every query, but saves in state
)

@router.get("/", tags=ROUTE_TAGS, name="about", description="about the " + ROUTE_NAME)
async def read_root():
    return {"database": "FILER"}

TAGS = ROUTE_TAGS +  ["Find Data Tracks"]
@router.get("/search", tags=TAGS, 
            name="Search for functional genomics tracks", 
            description="get metadata for all FILER tracks by datasource")
async def find_filer_tracks(sp: SharedParams):
    return {"tracks": "TODO: retrieve tracks by filter"}

# query(assembly = Depends(assembly_param), chromosome = Depends(chromosome_param), filter: Union[str, None] = None):


# --------------------------------------------------------------
# CHIILD ROUTES
# --------------------------------------------------------------
# router.include_router(metadata)
# router.include_router(data)