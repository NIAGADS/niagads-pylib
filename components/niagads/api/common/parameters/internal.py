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

from components.niagads.api.common.models.context.response import ResponseConfiguration
from components.niagads.api.common.services.pagination import PaginationService

# internal cache; stores responses as is
_CACHE_MANAGER = KeyDBCacheManager(
    connection_string=Settings.from_env().CACHE_DB_URI,
    serializer=CacheSerializer.PICKLE,
    ttl=Settings.from_env().CACHE_TTL,
)


class EndpointContext(BaseModel, arbitrary_types_allowed=True):
    """Provide request-scoped context and service dependencies to endpoints.

    This model is injected into endpoint handlers and supplies request metadata,
    cache access, and optional HTTP and database sessions.
    """

    request: Request
    request_data: RequestDetails = Depends(RequestDetails.from_request)

    cache_key: CacheKey = Depends(CacheKey.from_request)
    cache_manager: Annotated[KeyDBCacheManager, Depends(_CACHE_MANAGER)]

    pagination_service_type: Optional[type[PaginationService]] = None

    # session managers; callable to return none, override as needed for each endpoint
    http_client_session: Optional[ClientSession] = Depends(get_none)
    database_session: Optional[AsyncSession] = Depends(get_none)
