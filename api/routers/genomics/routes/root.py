from fastapi import APIRouter, Depends
from typing import Annotated
from sqlalchemy.ext.asyncio import AsyncSession

from api.common.exceptions import RESPONSES
from api.models.base_models import RequestDataModel
from api.models.base_response_models import BaseResponseModel

from ..common.constants import ROUTE_NAME, ROUTE_TAGS, ROUTE_PREFIX
from ..dependencies.parameters import ROUTE_SESSION_MANAGER

from .service import router as ServiceRouter

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
    
    return BaseResponseModel(response = {"database": "GenomicsDB"}, request=requestData)



# --------------------------------------------------------------
# CHIILD ROUTES
# --------------------------------------------------------------
router.include_router(ServiceRouter)
"""
router.include_router(TrackRouter)
router.include_router(MetadataRouter)
router.include_router(DataRouter)

router.include_router(CollectionRouter)
"""