from enum import auto
from typing import Annotated, List

from fastapi import Depends
from niagads.database.schemas.dataset.track import TrackDataStore
from niagads.database.session import DatabaseSessionManager
from niagads.enums.core import CaseInsensitiveEnum
from niagads.open_access_api_common.config.core import Settings
from niagads.open_access_api_common.parameters.internal import (
    InternalRequestParameters as _InternalRequestParameters,
)
from niagads.open_access_api_common.parameters.text_search import (
    TextSearchFilterParameter,
)

from niagads.settings.core import ServiceEnvironment, get_service_environment
from sqlalchemy.ext.asyncio import AsyncSession


ROUTE_SESSION_MANAGER: DatabaseSessionManager = DatabaseSessionManager(
    connectionString=Settings.from_env().APP_DB_URI,
    echo=get_service_environment() == ServiceEnvironment.DEV,
)


class InternalRequestParameters(
    _InternalRequestParameters, arbitrary_types_allowed=True
):
    session: Annotated[AsyncSession, Depends(ROUTE_SESSION_MANAGER)]


TRACK_DATA_STORES: List[TrackDataStore] = [
    TrackDataStore.GENOMICS,
    TrackDataStore.SHARED,
]


class TextSearchFilterFields(CaseInsensitiveEnum):
    DISEASE = auto()
    RACE = auto()
    ETHNICITY = auto()
    NEUROPATHOLOGY = auto()
    # DATA_CATEGORY = auto()


TEXT_FILTER_PARAMETER = TextSearchFilterParameter(TextSearchFilterFields)
