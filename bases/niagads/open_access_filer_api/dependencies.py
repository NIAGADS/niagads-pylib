from typing import Annotated, List

from aiohttp import ClientSession
from fastapi import Depends
from niagads.database.models.metadata.composite_attributes import TrackDataStore
from niagads.database.session.core import DatabaseSessionManager
from niagads.open_access_api_common.config.core import Settings
from niagads.open_access_api_common.parameters.internal import (
    InternalRequestParameters as _InternalRequestParameters,
)
from niagads.requests.core import HttpClientSessionManager
from sqlalchemy.ext.asyncio import AsyncSession

_HTTP_CLIENT_TIMEOUT = 60

ROUTE_SESSION_MANAGER: DatabaseSessionManager = DatabaseSessionManager(
    connectionString=Settings.get().APP_DB_URI
)

API_CLIENT_SESSION_MANAGER = HttpClientSessionManager(
    Settings.get().EXTERNAL_REQUEST_URL, timeout=_HTTP_CLIENT_TIMEOUT
)


class InternalRequestParameters(
    _InternalRequestParameters, arbitrary_types_allowed=True
):
    session: Annotated[AsyncSession, Depends(ROUTE_SESSION_MANAGER)]
    apiClientSession: Annotated[ClientSession, Depends(API_CLIENT_SESSION_MANAGER)]


TRACK_DATA_STORES: List[TrackDataStore] = [TrackDataStore.FILER, TrackDataStore.SHARED]
