from collections.abc import AsyncGenerator
from typing import Annotated

from aiohttp import ClientSession
from fastapi import Depends, Request
from niagads.api.common.config import Settings
from niagads.api.common.parameters.internal import EndpointContext
from niagads.requests.core import HttpClientSessionManager


async def get_bin_index_reference(request: Request) -> dict:
    """Retrieve the shared interval-bin reference from application state.

    Args:
        request (Request): Request associated with the initialized application.

    Returns:
        dict: Reference mapping loaded during application startup.
    """
    return request.app.state.bin_index_reference


async def get_http_client_sessions() -> AsyncGenerator[dict[str, ClientSession]]:
    """Provide HTTP client sessions and close them after the request.

    Yields:
        dict[str, ClientSession]: Sessions keyed by external service name.
    """
    async with HttpClientSessionManager(
        Settings.from_env().FILER_REQUEST_URL,
        timeout=60,
    ) as filer_manager:
        yield {"filer": await filer_manager()}
    # xqtl_manager = HttpClientSessionManager(
    #     Settings.from_env().XQTL_REQUEST_URL,
    #     timeout=60,
    # )


class OpenAccessEndpointContext(EndpointContext):
    http_client_session: Annotated[
        dict[str, ClientSession],
        Depends(get_http_client_sessions),
    ]
