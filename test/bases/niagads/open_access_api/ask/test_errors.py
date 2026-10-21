"""API failures preserve diagnostics without custom exception classification."""

import asyncio

import httpx
import pytest
from fastapi import FastAPI
from niagads.api.common.exception_handlers import add_runtime_exception_handler
from niagads.open_access_api.ask.api_client import retrieve


@pytest.mark.parametrize("status", [401, 403, 422, 429, 500, 501, 503, 504])
def test_api_failures_include_status_and_response_details(status):
    async def run():
        async with httpx.AsyncClient(
            transport=httpx.MockTransport(
                lambda _: httpx.Response(status, json={"detail": "service-detail"})
            ),
            base_url="http://api",
        ) as client:
            with pytest.raises(RuntimeError) as caught:
                await retrieve(client, "track", {"track": "track-1"})
            assert f"HTTP {status}" in str(caught.value)
            assert "service-detail" in str(caught.value)

    asyncio.run(run())


def test_internal_api_runtime_error_retains_handler_diagnostics():
    app = FastAPI()
    add_runtime_exception_handler(app)

    @app.get("/record/track/{track}")
    async def fail(track: str):
        raise RuntimeError("database connection failed")

    async def run():
        async with httpx.AsyncClient(
            transport=httpx.ASGITransport(app=app), base_url="http://api"
        ) as client:
            with pytest.raises(RuntimeError) as caught:
                await retrieve(client, "track", {"track": "test"})
            assert "database connection failed" in str(caught.value)
            assert "stack_trace" in str(caught.value)

    asyncio.run(run())


def test_record_not_found_is_an_empty_result():
    async def run():
        async with httpx.AsyncClient(
            transport=httpx.MockTransport(lambda _: httpx.Response(404)),
            base_url="http://api",
        ) as client:
            result = await retrieve(client, "track", {"track": "missing-track"})
            assert result.rows == []

    asyncio.run(run())


def test_success_status_with_error_body_retains_details():
    async def run():
        async with httpx.AsyncClient(
            transport=httpx.MockTransport(
                lambda _: httpx.Response(200, json={"error": "provider-detail"})
            ),
            base_url="http://api",
        ) as client:
            with pytest.raises(RuntimeError, match="provider-detail"):
                await retrieve(client, "track", {"track": "test"})

    asyncio.run(run())


def test_internal_asgi_call_has_an_enforced_deadline():
    app = FastAPI()

    @app.get("/record/track/{track}")
    async def delayed(track: str):
        await asyncio.sleep(1)
        return {"data": []}

    async def run():
        async with httpx.AsyncClient(
            transport=httpx.ASGITransport(app=app),
            base_url="http://api",
            timeout=0.01,
        ) as client:
            with pytest.raises(RuntimeError, match="TimeoutError"):
                await retrieve(client, "track", {"track": "test"})

    asyncio.run(run())
