"""Feedback validation and response-trace correlation without model calls."""

from unittest.mock import MagicMock

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from niagads.open_access_api.ask.config import AskSettings
from niagads.open_access_api.ask.feedback import create_feedback_reference
from niagads.open_access_api.ask.transport import get_settings, router
from opentelemetry import trace
from pydantic import SecretStr

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
