from fastapi import APIRouter, Depends
from fastapi import Depends
from sqlmodel import select
from typing import Union, Annotated, Optional

from api.dependencies.location_params import assembly_param, chromosome_param
from api.dependencies.exceptions import RESPONSES
from api.dependencies.database import DBSession

from .dependencies import ROUTE_ABBREVIATION, ROUTE_NAME, ROUTE_TAGS, ROUTE_PREFIX, CacheQueryService as Service
from .track import router as TrackRouter
from .query import router as QueryRouter

router = APIRouter(
    prefix=ROUTE_PREFIX,
    tags=ROUTE_TAGS,
    responses=RESPONSES,
    # dependencies=[Depends(get_db('filer'))] # adds dependencies to every query, but saves in state
)

@router.get("/", tags=ROUTE_TAGS, name="about", description="about the " + ROUTE_NAME)
async def read_root(service: Annotated[Service, Depends(Service)]):
    numTracks = service.get_count()
    return {"database": "FILER", "number of tracks": numTracks}




# --------------------------------------------------------------
# CHIILD ROUTES
# --------------------------------------------------------------
router.include_router(TrackRouter)
router.include_router(QueryRouter)
# router.include_router(data)