from typing import Annotated, Optional

from aiohttp import ClientSession
from fastapi import Depends, Request
from niagads.cache.core import KeyDBCacheManager, CacheSerializer
from niagads.open_access_api_common.config.core import get_settings
from niagads.open_access_api_common.dependencies import get_none
from niagads.open_access_api_common.models.cache import CacheKeyDataModel
from niagads.open_access_api_common.models.response.request import RequestDataModel
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

# internal cache; stores responses as is
__CACHE_MANAGER = KeyDBCacheManager(
    serializer=CacheSerializer.PICKLE, ttl=get_settings().CACHE_TTL
)


class InternalRequestParameters(BaseModel, arbitrary_types_allowed=True):
    request: Request
    requestData: RequestDataModel = Depends(RequestDataModel.from_request)

    cacheKey: CacheKeyDataModel = Depends(CacheKeyDataModel.from_request)
    cache: Annotated[KeyDBCacheManager, Depends(__CACHE_MANAGER)]

    # session managers; callable to return none, override as needed for each endpoint
    apiClientSession: Optional[ClientSession] = Depends(get_none)
    session: Optional[AsyncSession] = Depends(get_none)
