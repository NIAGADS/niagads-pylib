from enum import auto
from typing import Annotated, List

from aiohttp import ClientSession
from fastapi import Depends
from niagads.database.schemas.dataset.track import TrackDataStore
from niagads.database.session import DatabaseSessionManager
from niagads.enums.core import CaseInsensitiveEnum
from niagads.api_common.config import Settings
from niagads.api_common.parameters.internal import (
    InternalRequestParameters as _InternalRequestParameters,
)
from niagads.api_common.parameters.text_search import (
    TextSearchFilterParameter,
)
from niagads.requests.core import HttpClientSessionManager
from niagads.settings.core import ServiceEnvironment, get_service_environment
from sqlalchemy.ext.asyncio import AsyncSession

_HTTP_CLIENT_TIMEOUT = 60

ROUTE_SESSION_MANAGER: DatabaseSessionManager = DatabaseSessionManager(
    connection_string=Settings.from_env().APP_DB_URI,
    echo=get_service_environment() == ServiceEnvironment.DEV,
)

API_CLIENT_SESSION_MANAGER = HttpClientSessionManager(
    Settings.from_env().EXTERNAL_REQUEST_URL, timeout=_HTTP_CLIENT_TIMEOUT
)


class InternalRequestParameters(
    _InternalRequestParameters, arbitrary_types_allowed=True
):
    session: Annotated[AsyncSession, Depends(ROUTE_SESSION_MANAGER)]
    api_client_session: Annotated[ClientSession, Depends(API_CLIENT_SESSION_MANAGER)]


TRACK_DATA_STORES: List[TrackDataStore] = [TrackDataStore.FILER, TrackDataStore.SHARED]


class TextSearchFilterFields(CaseInsensitiveEnum):
    DATA_SOURCE = auto()
    ASSAY = auto()
    FEATURE_TYPE = auto()
    ANTIBODY_TARGET = auto()
    DATA_CATEGORY = auto()
    BIOSAMPLE_TYPE = auto()
    TISSUE = auto()
    CELL = auto()


TEXT_FILTER_PARAMETER = TextSearchFilterParameter(TextSearchFilterFields)
