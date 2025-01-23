from fastapi import Depends, Path, Query
from typing import Annotated
from sqlalchemy.ext.asyncio import AsyncSession
from aiohttp import ClientSession

from api.config.settings import get_settings
from api.common.enums import ResponseFormat
from api.common.formatters import clean, print_enum_values
from api.dependencies.database import DatabaseSessionManager
from api.dependencies.http_client import HttpClientSessionManager
from api.dependencies.parameters.optional import get_response_format
from api.dependencies.parameters.services import InternalRequestParameters as BaseInternalRequestParameters

from ..common.constants import FILER_HTTP_CLIENT_TIMEOUT, ROUTE_DATABASE

# initialize database and api wrapper session managers; this allows us to 
# use connection pooling
ROUTE_SESSION_MANAGER = DatabaseSessionManager(ROUTE_DATABASE)
API_CLIENT_SESSION_MANAGER = HttpClientSessionManager(get_settings().FILER_REQUEST_URI, timeout=FILER_HTTP_CLIENT_TIMEOUT)
class InternalRequestParameters(BaseInternalRequestParameters, arbitrary_types_allowed=True):
    session: Annotated[AsyncSession, Depends(ROUTE_SESSION_MANAGER)]
    apiClientSession: Annotated[ClientSession, Depends(API_CLIENT_SESSION_MANAGER)]

async def path_track_id(track: str = Path(description="FILER track identifier")) -> str:
    return clean(track)

async def query_track_id(track: str = Query(description="comma separated list of one or more FILER track identifiers")) -> str:
    return clean(track)

get_non_data_format_enum = get_response_format(exclude=[ResponseFormat.IGV_BROWSER])

async def non_data_format_param(format: str = Query(ResponseFormat.JSON, 
    description=f'response content; one of: {print_enum_values(get_non_data_format_enum)}')) -> str:
    return format