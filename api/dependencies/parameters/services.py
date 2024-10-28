from typing import Annotated
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession
from fastapi import Depends
from aiocache import RedisCache

from api.response_models.base_models import RequestDataModel
from api.common.formatters import clean
from ..database import CacheManager, CacheSerializer

# internal cache; stores responses as is 
INTERNAL_CACHE = CacheManager(serializer=CacheSerializer.PICKLE)

# for cache data that will be accessed by external applications (e.g., next.js)
EXTERNAL_CACHE = CacheManager(serializer=CacheSerializer.JSON) 
class InternalRequestParameters(BaseModel, arbitrary_types_allowed=True):
    requestData: RequestDataModel = Depends(RequestDataModel.from_request)
    session: AsyncSession
    internalCacheKey: str = Depends(RequestDataModel.cache_key)
    internalCache: Annotated[RedisCache, Depends(INTERNAL_CACHE)]
    externalCache: Annotated[RedisCache, Depends(EXTERNAL_CACHE)] 

