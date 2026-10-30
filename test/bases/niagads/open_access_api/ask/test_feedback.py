"""Feedback validation and response-trace correlation without model calls."""

import json
from contextlib import nullcontext
from unittest.mock import MagicMock

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from niagads.open_access_api.ask.config import AskSettings
from niagads.open_access_api.ask.feedback import create_feedback_reference
from niagads.open_access_api.ask.transport import get_agent, get_settings, router
from opentelemetry import trace
from pydantic import SecretStr
from pydantic_ai import Agent
from pydantic_ai.models.test import TestModel
from pydantic_ai.ui.vercel_ai import VercelAIAdapter
from pydantic_ai.ui.vercel_ai.response_types import ErrorChunk, StartChunk

TRACEPARENT = "00-" + "1" * 32 + "-" + "2" * 16 + "-01"


@pytest.fixture
def feedback_client(monkeypatch):
    settings = AskSettings(feedback_enable=True)
    app = FastAPI()
    app.include_router(router)
    app.state.ask_telemetry_enabled = True
    app.state.ask_feedback_signing_secret = SecretStr("test-feedback-secret")
    app.dependency_overrides[get_settings] = lambda: settings
    monkeypatch.setattr(
        "niagads.open_access_api.ask.feedback.logfire.get_context",
        lambda: {"traceparent": TRACEPARENT},
    )
    return TestClient(app)


@pytest.mark.parametrize("rating,comment", [(1, None), (0, "Missing evidence")])
def test_feedback_links_rating_to_original_response(
    feedback_client, monkeypatch, rating, comment
):
    emissions = []
    logger = MagicMock()
    logger.emit.side_effect = lambda **event: emissions.append(
        (trace.get_current_span().get_span_context(), event)
    )
    monkeypatch.setattr(
        "niagads.open_access_api.ask.feedback.get_logger", lambda name: logger
    )
    reference = create_feedback_reference(SecretStr("test-feedback-secret"))
    response = feedback_client.post(
        "/ask/feedback",
        json={"reference": reference, "rating": rating, "comment": comment},
    )

    assert response.status_code == 204
    context, event = emissions[0]
    assert context.trace_id == int("1" * 32, 16)
    assert context.span_id == int("2" * 16, 16)
    assert event["event_name"] == "gen_ai.evaluation.result"
    assert event["attributes"]["gen_ai.evaluation.score.value"] == rating
    assert event["attributes"].get("gen_ai.evaluation.explanation") == comment


def test_feedback_rejects_modified_signature(feedback_client, monkeypatch):
    logger = MagicMock()
    monkeypatch.setattr(
        "niagads.open_access_api.ask.feedback.get_logger", lambda name: logger
    )
    reference = create_feedback_reference(SecretStr("another-worker-secret"))
    response = feedback_client.post(
        "/ask/feedback", json={"reference": reference, "rating": 1}
    )

    assert response.status_code == 422
    logger.emit.assert_not_called()


@pytest.mark.parametrize(
    "changes",
    [{"rating": 2}, {"comment": "x" * 2001}, {"reference": "forged"}],
)
def test_feedback_rejects_invalid_input(feedback_client, changes):
    payload = {
        "reference": create_feedback_reference(SecretStr("test-feedback-secret")),
        "rating": 1,
    }
    response = feedback_client.post("/ask/feedback", json=payload | changes)

    assert response.status_code == 422


def test_feedback_unavailable_without_telemetry(feedback_client):
    feedback_client.app.state.ask_telemetry_enabled = False
    response = feedback_client.post(
        "/ask/feedback",
        json={
            "reference": create_feedback_reference(SecretStr("test-feedback-secret")),
            "rating": 0,
        },
    )

    assert response.status_code == 503


def test_feedback_reference_requires_sampled_context(monkeypatch):
    monkeypatch.setattr(
        "niagads.open_access_api.ask.feedback.logfire.get_context", lambda: {}
    )

    assert create_feedback_reference(SecretStr("test-feedback-secret")) is None


def test_feedback_can_be_explicitly_disabled(feedback_client):
    feedback_client.app.dependency_overrides[get_settings] = lambda: AskSettings(
        feedback_enable=False
    )
    response = feedback_client.post(
        "/ask/feedback",
        json={
            "reference": create_feedback_reference(SecretStr("test-feedback-secret")),
            "rating": 1,
        },
    )

    assert response.status_code == 503


async def error_chunk_events(*args, **kwargs):
    """Simulate an adapter-reported failure after starting a response."""
    yield StartChunk(message_id="failed-answer")
    yield ErrorChunk(error_text="Retrieval failed")


async def exception_events(*args, **kwargs):
    """Simulate an exception after starting a response."""
    yield StartChunk(message_id="failed-answer")
    raise RuntimeError("Retrieval failed")


@pytest.mark.parametrize("failure", ["error_chunk", "exception"])
def test_failed_responses_include_feedback_reference(
    feedback_client, monkeypatch, failure
):
    agent = Agent(TestModel())
    feedback_client.app.dependency_overrides[get_agent] = lambda: agent
    monkeypatch.setattr(
        "niagads.open_access_api.ask.transport.logfire.span",
        lambda *args, **kwargs: nullcontext(),
    )
    monkeypatch.setattr(
        VercelAIAdapter, "run_stream_native", lambda *args, **kwargs: None
    )
    monkeypatch.setattr(
        VercelAIAdapter,
        "transform_stream",
        error_chunk_events if failure == "error_chunk" else exception_events,
    )

    response = feedback_client.post(
        "/ask",
        json={
            "messages": [{"role": "user", "parts": [{"type": "text", "text": "APOE"}]}]
        },
    )
    assert response.status_code == 200
    events = [
        json.loads(line.removeprefix("data: "))
        for line in response.iter_lines()
        if line.startswith("data: ") and line != "data: [DONE]"
    ]
    result_events = [
        event for event in events if event["type"] == "data-niagads-result"
    ]
    assert len(result_events) == 1
    assert "id" not in result_events[0]
    assert "transient" not in result_events[0]
    result = result_events[0]["data"]
    assert result["status"] == "retrieval_error"
    assert result["results"] == []
    assert result["feedback_reference"] == create_feedback_reference(
        SecretStr("test-feedback-secret")
    )
    types = [event["type"] for event in events]
    assert (
        types.index("start") < types.index("data-niagads-result") < types.index("error")
    )
