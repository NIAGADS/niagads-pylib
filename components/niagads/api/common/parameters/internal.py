from typing import Annotated, Optional

from aiohttp import ClientSession
from fastapi import Depends, Request
from niagads.api.common.config import Settings
from niagads.api.common.models.context.cache import CacheKey
from niagads.api.common.models.context.request import RequestDetails
from niagads.api.common.utils import get_none
from niagads.cache.core import CacheSerializer, KeyDBCacheManager
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
    request_data: RequestDetails = Depends(RequestDetails.from_request)

    cache_key: CacheKey = Depends(CacheKey.from_request)
    cache_manager: Annotated[KeyDBCacheManager, Depends(_CACHE_MANAGER)]

    # session managers; callable to return none, override as needed for each endpoint
    http_client_session: Optional[ClientSession] = Depends(get_none)
    database_session: Optional[AsyncSession] = Depends(get_none)
