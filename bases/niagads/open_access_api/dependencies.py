from typing import Annotated

from aiohttp import ClientSession
from fastapi import Depends
from niagads.api.common.config import Settings
from niagads.api.common.parameters.internal import EndpointContext
from niagads.requests.core import HttpClientSessionManager


async def get_http_client_sessions() -> dict[str, ClientSession]:
    return {
        "filer": await HttpClientSessionManager(
            Settings.from_env().FILER_REQUEST_URL, timeout=60
        ),
    }


class OpenAccessEndpointContext(EndpointContext):
    http_client_session: Annotated[
        dict[str, ClientSession],
        Depends(get_http_client_sessions),
    ]
