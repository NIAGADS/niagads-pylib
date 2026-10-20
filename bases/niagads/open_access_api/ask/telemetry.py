"""Optional, content-redacted Logfire instrumentation for the prototype."""

import logging
import os

import logfire
from fastapi import FastAPI
from niagads.open_access_api.ask.config import AskSettings
from pydantic import ValidationError


def configure_telemetry(app: FastAPI, settings: AskSettings | None = None) -> bool:
    """Instrument before startup when configured; failures never block the API."""
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
    if not settings.telemetry or not os.environ.get("LOGFIRE_TOKEN"):
        return False
    try:
        patterns = (
            None
            if settings.capture_content
            else [
                r"(?i:url\.full|url\.query|http\.url|http\.target|arguments|query_string|request_data|request[._]body|json_data)"
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
        return True
    except Exception:
        logging.getLogger(__name__).warning(
            "Assistant telemetry could not be initialized", exc_info=True
        )
        return False
