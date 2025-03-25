from fastapi import Depends, Path, Query
from typing import Annotated, Optional
from fastapi.exceptions import RequestValidationError
from sqlalchemy.ext.asyncio import AsyncSession
from aiohttp import ClientSession

from api.config.settings import get_settings
from api.common.enums.response_properties import ResponseFormat
from api.common.formatters import clean
from api.dependencies.database import DatabaseSessionManager
from api.dependencies.http_client import HttpClientSessionManager
from api.dependencies.parameters.filters import ExpressionType, FilterParameter
from api.dependencies.parameters.services import InternalRequestParameters as BaseInternalRequestParameters

from api.routers.filer.common.constants import FILER_HTTP_CLIENT_TIMEOUT, ROUTE_DATABASE, TRACK_SEARCH_FILTER_FIELD_MAP

# initialize database and api wrapper session managers; this allows us to 
# use connection pooling
ROUTE_SESSION_MANAGER = DatabaseSessionManager(ROUTE_DATABASE)
API_CLIENT_SESSION_MANAGER = HttpClientSessionManager(get_settings().FILER_REQUEST_URI, timeout=FILER_HTTP_CLIENT_TIMEOUT)
class InternalRequestParameters(BaseInternalRequestParameters, arbitrary_types_allowed=True):
    session: Annotated[AsyncSession, Depends(ROUTE_SESSION_MANAGER)]
    apiClientSession: Annotated[ClientSession, Depends(API_CLIENT_SESSION_MANAGER)]



async def required_query_track_id(track: str = Query(description="comma separated list of one or more FILER track identifiers")) -> str:
    return clean(track)

async def optional_query_track_id(track: Optional[str] = Query(default=None, description="comma separated list of one or more FILER track identifiers")) -> str:
    return clean(track)

async def optional_query_track_id_single(track: Optional[str] = Query(default=None, description="a FILER track identifier")) -> str:
    if track is not None and ',' in track:
        raise RequestValidationError('Lists of track identifiers not allowed for this query.  Please provide a single `track` identifier.')
    return clean(track)

METADATA_FILTER_PARAM = FilterParameter(TRACK_SEARCH_FILTER_FIELD_MAP, ExpressionType.TEXT)