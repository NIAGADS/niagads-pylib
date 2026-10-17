from typing import Annotated

from aiohttp import ClientSession
from fastapi import Depends
from niagads.api.common.config import Settings
from niagads.api.common.parameters.internal import EndpointContext
from niagads.api.common.services.endpoint import EndpointService
from niagads.database.session import DatabaseSessionManager
from niagads.requests.core import HttpClientSessionManager
from niagads.settings.core import ServiceEnvironment, get_service_environment


async def get_http_client_sessions() -> dict[str, ClientSession]:
    return {
        "filer": await HttpClientSessionManager(
            Settings.from_env().FILER_REQUEST_URL, timeout=60
        ),
    }


class OpenAccessContext(EndpointContext):
    http_client_session: Annotated[
        dict[str, ClientSession],
        Depends(get_http_client_sessions),
    ]
