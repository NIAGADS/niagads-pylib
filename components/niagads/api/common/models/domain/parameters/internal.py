from typing import Annotated, Optional

from aiohttp import ClientSession
from fastapi import Depends, Request
from niagads.api.common.models.service.cache import CacheKeyDataModel
from niagads.api.common.models.service.request import RequestDataModel
from niagads.cache.core import KeyDBCacheManager, CacheSerializer
from niagads.api.common.config import Settings
from niagads.api.common.dependencies import get_none

from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

# internal cache; stores responses as is
_CACHE_MANAGER = KeyDBCacheManager(
    connection_string=Settings.from_env().CACHE_DB_URI,
    serializer=CacheSerializer.PICKLE,
    ttl=Settings.from_env().CACHE_TTL,
)


class InternalRequestParameters(BaseModel, arbitrary_types_allowed=True):
    request: Request
    request_data: RequestDataModel = Depends(RequestDataModel.from_request)

    cache_key: CacheKeyDataModel = Depends(CacheKeyDataModel.from_request)
    cache: Annotated[KeyDBCacheManager, Depends(_CACHE_MANAGER)]

    # session managers; callable to return none, override as needed for each endpoint
    api_client_session: Optional[ClientSession] = Depends(get_none)
    session: Optional[AsyncSession] = Depends(get_none)
