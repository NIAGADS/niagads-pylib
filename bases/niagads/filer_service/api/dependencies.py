from enum import auto
from typing import Annotated

from aiohttp import ClientSession
from fastapi import Depends
from niagads.api.common.models.domain.parameters.internal import (
    InternalRequestParameters,
)
from niagads.api.common.models.domain.parameters.text_search import (
    TextSearchFilterParameter,
)
from niagads.database import DatabaseSessionManager
from niagads.enums.core import CaseInsensitiveEnum
from niagads.api.common.config import Settings
from niagads.requests.core import HttpClientSessionManager
from niagads.settings.core import ServiceEnvironment, get_service_environment
from sqlalchemy.ext.asyncio import AsyncSession

_HTTP_CLIENT_TIMEOUT = 60

FILERDatabaseSessionManager: DatabaseSessionManager = DatabaseSessionManager(
    connection_string=Settings.from_env().APP_DB_URI,
    echo=get_service_environment() == ServiceEnvironment.DEV,
)

FILERHttpClientSessionManager = HttpClientSessionManager(
    Settings.from_env().EXTERNAL_REQUEST_URL, timeout=_HTTP_CLIENT_TIMEOUT
)


class FILEREndpointRequestParameters(
    InternalRequestParameters, arbitrary_types_allowed=True
):
    database_session: Annotated[AsyncSession, Depends(FILERDatabaseSessionManager)]
    http_client_session: Annotated[
        ClientSession, Depends(FILERHttpClientSessionManager)
    ]


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
