from typing import Annotated, Optional
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession
from fastapi import Depends, Request

from api.response_models.base_models import CacheKeyDataModel, RequestDataModel
from api.common.formatters import clean
from ..database import CacheManager, CacheSerializer

# internal cache; stores responses as is 
INTERNAL_CACHE = CacheManager(serializer=CacheSerializer.PICKLE)

# for cache data that will be accessed by external applications (e.g., next.js)
EXTERNAL_CACHE = CacheManager(serializer=CacheSerializer.JSON) 

def get_none():
    return None

class InternalRequestParameters(BaseModel, arbitrary_types_allowed=True):
    requestData: RequestDataModel = Depends(RequestDataModel.from_request)
    session: Optional[AsyncSession] = Depends(get_none) # callable to return none, override as needed for each endpoint
    cacheKey: CacheKeyDataModel = Depends(CacheKeyDataModel.from_request)
    internalCache: Annotated[CacheManager, Depends(INTERNAL_CACHE)]
    externalCache: Annotated[CacheManager, Depends(EXTERNAL_CACHE)] 

