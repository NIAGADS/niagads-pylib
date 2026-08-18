from typing import Annotated, Optional

from aiohttp import ClientSession
from fastapi import Depends, Request
from niagads.api.common.config import Settings
from niagads.api.common.dependencies import get_none
from niagads.api.common.models.context.cache import CacheKeyDataModel
from niagads.api.common.models.context.request import RequestDataModel
from niagads.api.common.services.cache import CacheService
from niagads.cache.core import CacheSerializer, KeyDBCacheManager
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

# internal cache; stores responses as is
_CACHE_MANAGER = KeyDBCacheManager(
    connection_string=Settings.from_env().CACHE_DB_URI,
    serializer=CacheSerializer.PICKLE,
    ttl=Settings.from_env().CACHE_TTL,
)


def _CACHE_SERVICE(
    cache: Annotated[KeyDBCacheManager, Depends(_CACHE_MANAGER)],
    cache_key: CacheKeyDataModel = Depends(CacheKeyDataModel.from_request),
):
    return CacheService(cache, cache_key)


class InternalRequestParameters(BaseModel, arbitrary_types_allowed=True):
    request: Request
    request_data: RequestDataModel = Depends(RequestDataModel.from_request)

    cache_service: Annotated[CacheService, Depends(_CACHE_SERVICE)]

    # session managers; callable to return none, override as needed for each endpoint
    http_client_session: Optional[ClientSession] = Depends(get_none)
    database_session: Optional[AsyncSession] = Depends(get_none)
