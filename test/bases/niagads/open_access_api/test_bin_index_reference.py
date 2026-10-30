from typing import Annotated

from fastapi import Depends, Request
from fastapi.routing import APIRoute
from niagads.open_access_api.dependencies import get_bin_index_reference


async def reference_endpoint(
    request: Request,
    reference: Annotated[dict, Depends(get_bin_index_reference)],
) -> bool:
    """Check that dependency injection supplies the application reference.

    Args:
        request (Request): Request associated with the running application.
        reference (dict): Interval-bin reference supplied by the dependency.

    Returns:
        bool: Whether the dependency supplies the mapping in application state.
    """
    return reference is request.app.state.bin_index_reference


def test_bin_index_reference(client, monkeypatch):
    monkeypatch.setattr(
        client.app.router,
        "routes",
        [
            *client.app.routes,
            APIRoute("/test/reference", reference_endpoint, methods=["GET"]),
        ],
    )

    response = client.get("/test/reference")

    assert response.status_code == 200
    assert response.json() is True
