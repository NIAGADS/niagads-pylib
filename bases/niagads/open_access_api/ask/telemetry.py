"""Optional, content-redacted Logfire instrumentation for the prototype."""

import hmac
import logging
import os

import logfire
from fastapi import FastAPI
from niagads.open_access_api.ask.config import AskSettings
from pydantic import SecretStr, ValidationError


def configure_telemetry(app: FastAPI, settings: AskSettings | None = None) -> bool:
    """Instrument before startup when configured; failures never block the API."""
    app.state.ask_telemetry_enabled = False
    app.state.ask_feedback_signing_secret = None
    if settings is None:
        try:
            settings = AskSettings()
        except ValueError as exc:
            if isinstance(exc, ValidationError):
                logging.getLogger(__name__).warning(
                    "Assistant telemetry configuration is invalid: %s",
                    exc.errors(include_input=False, include_context=False),
                )
            else:
                logging.getLogger(__name__).warning(
                    "Assistant telemetry configuration is invalid", exc_info=True
                )
            return False
    logfire_token = os.environ.get("LOGFIRE_TOKEN")
    if not settings.telemetry or not logfire_token:
        return False
    try:
        patterns = (
            None
            if settings.capture_content
            else [
                r"(?i:url\.full|url\.query|http\.url|http\.target|arguments|"
                r"query_string|request_data|request[._]body|json_data)"
            ]
        )
        logfire.configure(
            send_to_logfire="if-token-present",
            scrubbing=logfire.ScrubbingOptions(extra_patterns=patterns),
        )
        logfire.instrument_fastapi(app, capture_headers=False)
        logfire.instrument_httpx(capture_all=False)
        logfire.instrument_pydantic_ai(
            include_content=settings.capture_content,
            include_binary_content=False,
        )
        app.state.ask_telemetry_enabled = True
        if settings.feedback_enable:
            app.state.ask_feedback_signing_secret = SecretStr(
                hmac.digest(
                    logfire_token.encode(), b"niagads.ask.feedback.v1", "sha256"
                ).hex()
            )
        return True
    except Exception:
        logging.getLogger(__name__).warning(
            "Assistant telemetry could not be initialized", exc_info=True
        )
        return False
