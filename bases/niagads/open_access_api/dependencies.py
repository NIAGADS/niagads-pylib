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


async def get_http_client_sessions() -> dict[str, ClientSession]:
    """Assemble client session mappings.  This overhead is so that
    we can support connections to multiple external APIs (e.g., FILER, xQTL)"""
    filer_manager = HttpClientSessionManager(
        Settings.from_env().FILER_REQUEST_URL,
        timeout=60,
    )
    # xqtl_manager = HttpClientSessionManager(
    #     Settings.from_env().XQTL_REQUEST_URL,
    #     timeout=60,
    # )
    return {"filer": await filer_manager()}


class OpenAccessEndpointContext(EndpointContext):
    http_client_session: Annotated[
        dict[str, ClientSession],
        Depends(get_http_client_sessions),
    ]
