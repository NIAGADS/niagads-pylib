from fastapi import APIRouter, Depends
from typing import Annotated
from sqlalchemy.ext.asyncio import AsyncSession
from api.dependencies.exceptions import RESPONSES


from .dependencies import ROUTE_NAME, ROUTE_TAGS, ROUTE_PREFIX, ROUTE_SESSION_MANAGER, MetadataQueryService
from .track import router as TrackRouter
from .query import router as QueryRouter

router = APIRouter(
    prefix=ROUTE_PREFIX,
    tags=ROUTE_TAGS,
    responses=RESPONSES,
    # dependencies=[Depends(get_db('filer'))] # adds dependencies to every query, but saves in state
)

@router.get("/", tags=ROUTE_TAGS, name="about", description="about the " + ROUTE_NAME)
async def read_root(session: Annotated[AsyncSession, Depends(ROUTE_SESSION_MANAGER)]):
    result = await MetadataQueryService(session).get_track_count()
    return {"database": "FILER", "number of tracks": result}




# --------------------------------------------------------------
# CHIILD ROUTES
# --------------------------------------------------------------
router.include_router(TrackRouter)
router.include_router(QueryRouter)
# router.include_router(data)