from typing import Annotated, Optional
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession
from fastapi import Depends, Request

from api.models.base_models import CacheKeyDataModel, RequestDataModel
from api.common.formatters import clean
from api.config.settings import get_settings
from ..database import CacheManager, CacheSerializer

# internal cache; stores responses as is 
CACHE_MANAGER = CacheManager(serializer=CacheSerializer.PICKLE, ttl=get_settings().CACHE_TTL)

def get_none():
    return None

class InternalRequestParameters(BaseModel, arbitrary_types_allowed=True):
    request: Request
    requestData: RequestDataModel = Depends(RequestDataModel.from_request)
    session: Optional[AsyncSession] = Depends(get_none) # callable to return none, override as needed for each endpoint
    cacheKey: CacheKeyDataModel = Depends(CacheKeyDataModel.from_request)
    cache: Annotated[CacheManager, Depends(CACHE_MANAGER)]


