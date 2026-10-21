"""OpenRouter retry protocol checks; no live provider or biological fixtures."""

import asyncio
import json
from datetime import datetime, timedelta, timezone
from email.utils import format_datetime
from types import SimpleNamespace

import httpx
import pytest
from fastapi import FastAPI
from niagads.open_access_api.ask import retries, transport
from niagads.open_access_api.ask.agent import build_agent
from niagads.open_access_api.ask.config import AskSettings
from niagads.open_access_api.ask.planning import QueryPlan
from niagads.open_access_api.ask.provider import build_model
from niagads.open_access_api.ask.retries import RetryingModel
from pydantic_ai.exceptions import ModelHTTPError
from pydantic_ai.messages import ModelRequest, UserPromptPart
from pydantic_ai.models import ModelRequestParameters
from pydantic_ai.models.function import FunctionModel
from pydantic_ai.models.openrouter import OpenRouterModel
from pydantic_ai.providers.openrouter import OpenRouterProvider


@pytest.mark.parametrize("status", [429, 500, 502, 503, 599])
def test_retry_schedule_statuses_and_original_final_error(status, monkeypatch):
    waits, states, calls = [], [], []
    error = ModelHTTPError(
        status_code=status,
        model_name="openrouter/free",
        body={"error": {"code": status}},
    )

    async def call():
        calls.append(True)
        raise error

    async def sleep(seconds):
        waits.append(seconds)

    monkeypatch.setattr(retries.asyncio, "sleep", sleep)
    monkeypatch.setattr(retries.random, "uniform", lambda a, b: 0.5)
    with pytest.raises(ModelHTTPError) as caught:
        asyncio.run(retries.call_with_retry(call, on_status=states.append))
    assert caught.value is error
    assert len(calls) == 5
    assert waits == [5.5, 15.5, 30.5, 60.5]
    assert [state.state for state in states] == [
        "requesting",
        "waiting",
        "retrying",
        "waiting",
        "retrying",
        "waiting",
        "retrying",
        "waiting",
        "retrying",
        "failed",
    ]
    assert [state.attempt for state in states if state.state == "retrying"] == [
        2,
        3,
        4,
        5,
    ]


@pytest.mark.parametrize("status", [400, 401, 403, 404, 408, 422])
def test_nonretryable_status_keeps_native_error(status):
    calls, states = [], []
    error = ModelHTTPError(
        status_code=status, model_name="openrouter/free", body="native diagnostic"
    )

    async def call():
        calls.append(True)
        raise error

    with pytest.raises(ModelHTTPError) as caught:
        asyncio.run(retries.call_with_retry(call, on_status=states.append))
    assert caught.value is error
    assert len(calls) == 1
    assert states[-1] is None


@pytest.mark.parametrize(
    "header",
    [
        "0",
        "12",
        format_datetime(
            datetime.now(timezone.utc) + timedelta(seconds=30), usegmt=True
        ),
        "invalid",
    ],
)
def test_retry_after_and_success_clear_status(header, monkeypatch):
    waits, states, calls = [], [], []
    error = ModelHTTPError(
        status_code=429,
        model_name="openrouter/free",
        body="busy",
        headers={"retry-after": header},
    )

    async def call():
        calls.append(True)
        if len(calls) == 1:
            raise error
        return "protocol response"

    async def sleep(seconds):
        waits.append(seconds)

    monkeypatch.setattr(retries.asyncio, "sleep", sleep)
    monkeypatch.setattr(retries.random, "uniform", lambda a, b: 0)
    assert (
        asyncio.run(retries.call_with_retry(call, on_status=states.append))
        == "protocol response"
    )
    assert states[-1] is None
    assert len(calls) == 2
    if header.isdecimal():
        assert waits == [float(header)]
    elif header == "invalid":
        assert waits == [5]
    else:
        assert 0 < waits[0] <= 30


def test_stop_cancels_backoff_without_another_call():
    calls = []

    async def run():
        waiting = asyncio.Event()

        async def call():
            calls.append(True)
            raise ModelHTTPError(
                status_code=429, model_name="openrouter/free", body="busy"
            )

        def status(value):
            if value is not None and value.state == "waiting":
                waiting.set()

        task = asyncio.create_task(retries.call_with_retry(call, on_status=status))
        await waiting.wait()
        task.cancel()
        with pytest.raises(asyncio.CancelledError):
            await task

    asyncio.run(run())
    assert len(calls) == 1


@pytest.mark.parametrize("mode", ["http", "body", "sse", "partial"])
def test_real_openrouter_sdk_retries_error_envelopes_before_response(mode, monkeypatch):
    calls, waits, states = [], [], []

    def completion(content):
        return {
            "id": "protocol",
            "object": "chat.completion",
            "provider": "Protocol provider",
            "created": 1,
            "model": "openrouter/free",
            "choices": [
                {
                    "index": 0,
                    "message": {"role": "assistant", "content": content},
                    "finish_reason": "stop",
                }
            ],
        }

    def chunk(content, reason=None):
        return {
            "id": "protocol",
            "object": "chat.completion.chunk",
            "created": 1,
            "model": "openrouter/free",
            "choices": [
                {"index": 0, "delta": {"content": content}, "finish_reason": reason}
            ],
        }

    def sse(value):
        return "data: " + json.dumps(value) + "\n\n"

    def handler(request):
        calls.append(request)
        error = {"error": {"code": 429, "message": "Protocol upstream busy"}}
        if len(calls) == 1:
            if mode == "http":
                return httpx.Response(503, json=error, headers={"Retry-After": "0"})
            if mode == "body":
                return httpx.Response(200, json=error, headers={"Retry-After": "12"})
            content = (
                sse(chunk("Already delivered")) if mode == "partial" else ""
            ) + sse(error)
            return httpx.Response(
                200,
                text=content,
                headers={"content-type": "text/event-stream", "Retry-After": "12"},
            )
        if mode in {"sse", "partial"}:
            return httpx.Response(
                200,
                text=sse(chunk("Protocol response", "stop")) + "data: [DONE]\n\n",
                headers={"content-type": "text/event-stream"},
            )
        return httpx.Response(200, json=completion("Protocol response"))

    async def sleep(seconds):
        waits.append(seconds)

    async def run():
        async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as client:
            provider = OpenRouterProvider(api_key="protocol-only", http_client=client)
            retries.configure_retry_client(provider.client)
            model = RetryingModel(OpenRouterModel("openrouter/free", provider=provider))
            token = retries.retry_status_callback.set(states.append)
            try:
                messages = [ModelRequest(parts=[UserPromptPart("Protocol request")])]
                if mode in {"sse", "partial"}:
                    async with model.request_stream(
                        messages, None, ModelRequestParameters()
                    ) as stream:
                        if mode == "partial":
                            with pytest.raises(ModelHTTPError):
                                async for event in stream:
                                    pass
                            return
                        async for event in stream:
                            pass
                        assert stream.get().parts[0].content == "Protocol response"
                else:
                    result = await model.request(
                        messages, None, ModelRequestParameters()
                    )
                    assert result.parts[0].content == "Protocol response"
            finally:
                retries.retry_status_callback.reset(token)

    monkeypatch.setattr(retries.asyncio, "sleep", sleep)
    asyncio.run(run())
    assert len(calls) == (1 if mode == "partial" else 2)
    assert len(waits) == (0 if mode == "partial" else 1)
    assert states[-1] is None
    if mode in {"body", "sse"}:
        assert waits == [12]


def test_backoff_pauses_active_deadline():
    async def run():
        calls = []
        async with asyncio.timeout(0.1) as deadline:
            token = retries.retry_deadline.set(deadline)
            try:

                async def call():
                    calls.append(True)
                    if len(calls) == 1:
                        raise ModelHTTPError(
                            status_code=429,
                            model_name="openrouter/free",
                            body="busy",
                            headers={"retry-after": "0.15"},
                        )
                    return "protocol response"

                assert await retries.call_with_retry(call) == "protocol response"
            finally:
                retries.retry_deadline.reset(token)
        assert len(calls) == 2

    asyncio.run(run())


def test_planner_retry_status_is_streamed_before_plan_and_cleared(monkeypatch):
    app = FastAPI()
    app.include_router(transport.router)
    settings = AskSettings(feedback_enable=False)
    agent = build_agent(
        settings, model=FunctionModel(stream_function=protocol_response)
    )
    app.dependency_overrides[transport.get_agent] = lambda: agent
    app.dependency_overrides[transport.get_settings] = lambda: settings
    calls = []

    async def planning_call():
        calls.append(True)
        if len(calls) == 1:
            raise ModelHTTPError(
                status_code=429,
                model_name="openrouter/free",
                body="Protocol busy",
                headers={"retry-after": "0"},
            )
        return SimpleNamespace(output=QueryPlan(intent="conversation"))

    async def plan(*args, **kwargs):
        return await retries.call_with_retry(planning_call)

    monkeypatch.setattr(
        transport, "build_query_planner", lambda model: SimpleNamespace(run=plan)
    )

    async def run():
        async with httpx.AsyncClient(
            transport=httpx.ASGITransport(app=app), base_url="http://test"
        ) as client:
            return await client.post(
                "/ask",
                json={
                    "messages": [
                        {"role": "user", "parts": [{"type": "text", "text": "Hello"}]}
                    ]
                },
            )

    response = asyncio.run(run())
    events = [
        json.loads(line[6:])
        for line in response.text.splitlines()
        if line.startswith("data: {")
    ]
    statuses = [
        event for event in events if event["type"] == "data-niagads-model-status"
    ]
    assert [
        event["data"]["state"] if event["data"] else None for event in statuses
    ] == ["requesting", "waiting", "retrying", None]
    assert all(event["transient"] for event in statuses)
    plan_index = next(
        i for i, event in enumerate(events) if event["type"] == "data-niagads-plan"
    )
    assert all(events.index(event) < plan_index for event in statuses)
    assert not [event for event in events if event["type"] == "error"]
    assert response.text.rstrip().endswith("data: [DONE]")


async def protocol_response(messages, info):
    yield "Protocol response."


def test_configured_model_keeps_router_and_uses_one_policy_with_native_client():
    async def run():
        model = build_model(
            AskSettings(
                model="openrouter/free",
                OPENROUTER_API_KEY="protocol-only",
                _env_file=None,
            )
        )
        async with model:
            assert model.model_name == "openrouter/free"
            assert model.provider.client.max_retries == 0
            assert (
                retries._capture_retry_after
                in model.provider.client._client.event_hooks["response"]
            )

    asyncio.run(run())
