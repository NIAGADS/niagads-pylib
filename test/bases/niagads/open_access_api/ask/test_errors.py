"""Failure distinctions and redacted diagnostics; no external services."""

import asyncio
from types import SimpleNamespace

import httpx
import pytest
from fastapi import FastAPI
from niagads.api.common.exception_handlers import add_runtime_exception_handler
from niagads.open_access_api.ask.api_client import retrieve
from niagads.open_access_api.ask.contracts import AskErrorCode
from niagads.open_access_api.ask.errors import RetrievalError, issue_for_provider_status
from niagads.open_access_api.ask.results import ResultStore
from niagads.open_access_api.ask.tools import _execute


@pytest.mark.parametrize(
    "status,code",
    [
        (422, "invalid_input"),
        (404, "not_found"),
        (401, "authentication"),
        (403, "authorization"),
        (429, "rate_limit"),
        (501, "unsupported"),
        (504, "timeout"),
        (502, "provider_error"),
        (500, "internal_error"),
    ],
)
def test_http_failures_keep_categories_without_forwarding_bodies(status, code):
    async def run():
        async with httpx.AsyncClient(
            transport=httpx.MockTransport(
                lambda _: httpx.Response(
                    status,
                    json={"detail": "secret-body", "stack_trace": ["secret"]},
                    headers={"X-Request-ID": "request-123"},
                )
            ),
            base_url="http://api",
        ) as client:
            with pytest.raises(RetrievalError) as caught:
                await retrieve(client, "track", {"track": "track-1"})
            issue = caught.value.issue
            assert issue.code == code
            assert issue.request_id == "request-123"
            assert "secret" not in issue.model_dump_json()
            assert "embedding" not in issue.message

    asyncio.run(run())


def test_handled_asgi_exception_is_preserved_without_changing_public_response():
    app = FastAPI()
    add_runtime_exception_handler(app)
    original = RuntimeError("secret-database-detail")

    @app.get("/record/track/{track}")
    async def fail(track: str):
        raise original

    async def run():
        async with httpx.AsyncClient(
            transport=httpx.ASGITransport(app=app),
            base_url="http://api",
        ) as client:
            direct = await client.get("/record/track/test")
            assert direct.json()["detail"] == "secret-database-detail"
            with pytest.raises(RetrievalError) as caught:
                await retrieve(client, "track", {"track": "test"})
            assert caught.value.__cause__ is original
            assert "secret" not in caught.value.issue.message

    asyncio.run(run())


def test_failure_is_not_empty_and_diagnostics_omit_sensitive_text(caplog):
    async def run():
        async with httpx.AsyncClient(
            transport=httpx.MockTransport(lambda _: httpx.Response(404)),
            base_url="http://api",
        ) as client:
            deps = {"client": client, "store": ResultStore(), "issues": []}
            result = await _execute(
                SimpleNamespace(deps=deps), "track", {"track": "secret"}
            )
            assert result["code"] == AskErrorCode.NOT_FOUND
            assert len(deps["issues"]) == 1
            assert not deps["store"].results

    asyncio.run(run())
    assert "secret" not in caplog.text
    assert "track" in caplog.text


@pytest.mark.parametrize(
    "status,code", [(401, "authentication"), (403, "authorization")]
)
def test_provider_access_failures_do_not_tell_the_browser_user_to_sign_in(status, code):
    issue = issue_for_provider_status(status, "search_genes", "api-ref", "provider-ref")
    assert issue.code == code
    assert "Contact support" in issue.message
    assert "Sign in" not in issue.message
    assert "retry" not in issue.message.lower()
    assert issue.provider_request_id == "provider-ref"


@pytest.mark.parametrize(
    "payload", [{"data": [], "pagination": "invalid"}, {"data": None}]
)
def test_malformed_success_response_is_not_an_empty_result(payload):
    async def run():
        async with httpx.AsyncClient(
            transport=httpx.MockTransport(lambda _: httpx.Response(200, json=payload)),
            base_url="http://api",
        ) as client:
            with pytest.raises(RetrievalError) as caught:
                await retrieve(client, "track", {"track": "test"})
            assert caught.value.issue.code == AskErrorCode.MALFORMED_RESPONSE

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
            with pytest.raises(RetrievalError) as caught:
                await retrieve(client, "track", {"track": "test"})
            assert caught.value.issue.code == AskErrorCode.TIMEOUT

    asyncio.run(run())
