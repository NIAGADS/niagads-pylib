from fastapi import Depends, Path, Query
from typing import Annotated, Optional
from fastapi.exceptions import RequestValidationError
from sqlalchemy.ext.asyncio import AsyncSession
from aiohttp import ClientSession

from api.common.constants import TRACK_SEARCH_FILTER_FIELD_MAP
from api.config.settings import Settings
from api.common.enums.response_properties import ResponseFormat
from api.common.formatters import clean
from api.dependencies.database import DatabaseSessionManager
from api.dependencies.http_client import HttpClientSessionManager
from api.dependencies.parameters.filters import ExpressionType, FilterParameter
from api.dependencies.parameters.services import (
    InternalRequestParameters as BaseInternalRequestParameters,
)

from api.routes.filer.common.constants import FILER_HTTP_CLIENT_TIMEOUT, ROUTE_DATABASE

# initialize database and api wrapper session managers; this allows us to
# use connection pooling
ROUTE_SESSION_MANAGER = DatabaseSessionManager(ROUTE_DATABASE)
API_CLIENT_SESSION_MANAGER = HttpClientSessionManager(
    Settings.from_env().EXTERNAL_REQUEST_URL, timeout=FILER_HTTP_CLIENT_TIMEOUT
)


class InternalRequestParameters(
    BaseInternalRequestParameters, arbitrary_types_allowed=True
):
    session: Annotated[AsyncSession, Depends(ROUTE_SESSION_MANAGER)]
    apiClientSession: Annotated[ClientSession, Depends(API_CLIENT_SESSION_MANAGER)]


async def required_query_track_id(
    track: str = Query(
        description="comma separated list of one or more FILER track identifiers"
    ),
) -> str:
    return sanitize(track)


async def optional_query_track_id(
    track: Optional[str] = Query(
        default=None,
        description="comma separated list of one or more FILER track identifiers",
    )
) -> str:
    return sanitize(track)


METADATA_FILTER_PARAM = FilterParameter(
    TRACK_SEARCH_FILTER_FIELD_MAP, ExpressionType.TEXT
)
