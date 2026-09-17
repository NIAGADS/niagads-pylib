from typing import Annotated, Optional

from aiohttp import ClientSession
from fastapi import Depends, Request
from niagads.api.common.config import Settings
from niagads.api.common.models.context.cache import CacheKey
from niagads.api.common.models.context.request import RequestDetails
from niagads.api.common.utils import get_none
from niagads.cache.core import CacheSerializer, KeyDBCacheManager
from niagads.database.session import DatabaseSessionManager
from niagads.settings.core import ServiceEnvironment, get_service_environment
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from components.niagads.api.common.models.context.response import ResponseConfiguration
from components.niagads.api.common.services.pagination import PaginationService

# internal cache; stores responses as is
__CACHE_MANAGER = KeyDBCacheManager(
    connection_string=Settings.from_env().CACHE_DB_URI,
    serializer=CacheSerializer.PICKLE,
    ttl=Settings.from_env().CACHE_TTL,
)

__DATABASE_SESSION_MANAGER: DatabaseSessionManager = DatabaseSessionManager(
    connection_string=Settings.from_env().APP_DB_URI,
    echo=get_service_environment() == ServiceEnvironment.DEV,
)


class EndpointContext(BaseModel, arbitrary_types_allowed=True):
    """Provide request-scoped context and service dependencies to endpoints.

    This model is injected into endpoint handlers and supplies request metadata,
    cache access, and optional HTTP and database sessions.
    """

    request: Request
    request_data: RequestDetails = Depends(RequestDetails.from_request)

    cache_key: CacheKey = Depends(CacheKey.from_request)
    cache_manager: Annotated[KeyDBCacheManager, Depends(__CACHE_MANAGER)]

    pagination_service_type: type[PaginationService] = PaginationService

    # session managers; override as needed for each endpoint
    http_client_session: Annotated[ClientSession, Depends(get_none)]
    database_session: Annotated[AsyncSession, Depends(__DATABASE_SESSION_MANAGER)]
