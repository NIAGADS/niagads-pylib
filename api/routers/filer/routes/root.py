from fastapi import APIRouter, Depends, Request
from typing import Annotated
from sqlalchemy.ext.asyncio import AsyncSession

from api.dependencies.exceptions import RESPONSES
from api.response_models import BaseResponseModel, RequestDataModel

from ..common.constants import ROUTE_NAME, ROUTE_TAGS, ROUTE_PREFIX
from ..common.services import MetadataQueryService
from ..dependencies import ROUTE_SESSION_MANAGER

from .track import router as TrackRouter
from .query import router as QueryRouter
from .metadata import router as MetadataRouter

router = APIRouter(
    prefix=ROUTE_PREFIX,
    tags=ROUTE_TAGS,
    responses=RESPONSES,
)

@router.get("/", tags=ROUTE_TAGS, name="about", response_model=BaseResponseModel,
            description="about the " + ROUTE_NAME)
async def read_root(
    session: Annotated[AsyncSession, Depends(ROUTE_SESSION_MANAGER)],
    requestData: RequestDataModel = Depends(RequestDataModel.from_request)
        )-> BaseResponseModel:
    
    result = await MetadataQueryService(session).get_track_count()
    return BaseResponseModel(response = {"database": "FILER", "number of tracks": result}, request=requestData)



# --------------------------------------------------------------
# CHIILD ROUTES
# --------------------------------------------------------------
router.include_router(TrackRouter)
router.include_router(QueryRouter)
router.include_router(MetadataRouter)
