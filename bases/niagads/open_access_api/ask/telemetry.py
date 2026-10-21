"""Optional, content-redacted Logfire instrumentation for the prototype."""

import logging
import os
import traceback

import httpx
import logfire
from fastapi import FastAPI
from niagads.open_access_api.ask.config import AskSettings
from niagads.open_access_api.ask.contracts import AskIssue
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
                r"(?i:url\.full|url\.query|http\.url|http\.target|arguments|"
                r"query_string|request_data|request[._]body|json_data|"
                r"exception[._](?:message|stacktrace)|error[._](?:message|stack))"
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


def log_failure(exc: Exception, issue: AskIssue) -> None:
    """Log exception chains and locations without content-bearing exception strings.

    Args:
        exc (Exception): The preserved original exception or wrapper.
        issue (AskIssue): Safe operation and correlation context.
    """
    chain = []
    seen = set()
    current = exc
    while current is not None and id(current) not in seen:
        seen.add(id(current))
        chain.append(
            {
                "type": type(current).__name__,
                "status": (
                    current.response.status_code
                    if isinstance(current, httpx.HTTPStatusError)
                    else getattr(
                        current, "status_code", getattr(current, "status", None)
                    )
                ),
                "frames": [
                    {
                        "file": frame.filename,
                        "line": frame.lineno,
                        "function": frame.name,
                    }
                    for frame in traceback.extract_tb(current.__traceback__)
                ],
            }
        )
        current = current.__cause__ or current.__context__
    logging.getLogger(f"uvicorn.error.{__name__}").warning(
        "ASK failure operation=%s code=%s request_id=%s "
        "provider_request_id=%s exceptions=%s",
        issue.operation,
        issue.code,
        issue.request_id,
        issue.provider_request_id,
        chain,
    )
