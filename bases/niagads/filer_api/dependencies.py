from typing import Annotated

from aiohttp import ClientSession
from fastapi import Depends
from niagads.api.common.config import Settings
from niagads.api.common.services.endpoint import EndpointService
from niagads.database.session import DatabaseSessionManager
from niagads.requests.core import HttpClientSessionManager
from niagads.settings.core import ServiceEnvironment, get_service_environment

__HTTP_CLIENT_TIMEOUT = 60

__FILER_SERVICE_CLIENT_MANAGER: HttpClientSessionManager = HttpClientSessionManager(
    Settings.from_env().EXTERNAL_REQUEST_URL, timeout=__HTTP_CLIENT_TIMEOUT
)


class FILEREndpointService(EndpointService):
    http_client_session: Annotated[
        ClientSession, Depends(__FILER_SERVICE_CLIENT_MANAGER)
    ]
