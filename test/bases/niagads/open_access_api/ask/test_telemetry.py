"""Optional telemetry cannot block serving queries."""

import logfire
from fastapi import FastAPI
from niagads.open_access_api.ask.config import AskSettings
from niagads.open_access_api.ask.telemetry import configure_telemetry


def test_no_credential_is_required_for_telemetry_disabled(monkeypatch):
    monkeypatch.delenv("LOGFIRE_TOKEN", raising=False)
    assert configure_telemetry(FastAPI(), AskSettings()) is False


def test_telemetry_setup_failure_is_nonfatal(monkeypatch):
    monkeypatch.setenv("LOGFIRE_TOKEN", "test-only-placeholder")

    def fail(**kwargs):
        raise RuntimeError("test instrumentation failure")

    monkeypatch.setattr(logfire, "configure", fail)
    assert configure_telemetry(FastAPI(), AskSettings(telemetry=True)) is False


def test_invalid_assistant_settings_do_not_break_other_api_routes(monkeypatch):
    monkeypatch.setenv("ASK_MODEL", "paid/model")
    assert configure_telemetry(FastAPI()) is False


def test_content_disabled_redacts_request_urls_and_arguments(monkeypatch):
    captured = {}
    monkeypatch.setenv("LOGFIRE_TOKEN", "test-only-placeholder")
    monkeypatch.setattr(logfire, "configure", lambda **kwargs: captured.update(kwargs))
    monkeypatch.setattr(logfire, "instrument_fastapi", lambda *args, **kwargs: None)
    monkeypatch.setattr(logfire, "instrument_httpx", lambda *args, **kwargs: None)
    monkeypatch.setattr(
        logfire, "instrument_pydantic_ai", lambda **kwargs: captured.update(kwargs)
    )
    assert configure_telemetry(FastAPI(), AskSettings(telemetry=True)) is True
    assert captured["include_content"] is False
    assert captured["scrubbing"].extra_patterns
