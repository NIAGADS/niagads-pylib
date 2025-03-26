from fastapi import APIRouter, Depends
from typing import Annotated
from sqlalchemy.ext.asyncio import AsyncSession

from api.common.exceptions import RESPONSES
from api.common.services.metadata_query import MetadataQueryService
from api.models.response_model_properties import RequestDataModel
from api.models.base_response_models import BaseResponseModel

from api.routes.filer.common.constants import ROUTE_NAME, ROUTE_TAGS, ROUTE_PREFIX
from api.routes.filer.dependencies.parameters import ROUTE_SESSION_MANAGER

from api.routes.filer.routes.track import router as TrackRouter
from api.routes.filer.routes.metadata import router as MetadataRouter
from api.routes.filer.routes.data import router as DataRouter
from api.routes.filer.routes.service import router as ServiceRouter
from api.routes.filer.routes.collection import router as CollectionRouter

router = APIRouter(
    prefix=ROUTE_PREFIX,
    tags=ROUTE_TAGS,
    responses=RESPONSES,
)

tags=['Route Information']
@router.get("/", name="about", response_model=BaseResponseModel, tags=tags,
            description="brief summary about the " + ROUTE_NAME)
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
router.include_router(MetadataRouter)
router.include_router(DataRouter)
router.include_router(ServiceRouter)
router.include_router(CollectionRouter)