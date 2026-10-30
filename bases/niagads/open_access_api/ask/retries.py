"""Bounded OpenRouter request retries with request-local progress callbacks."""

import asyncio
import logging
import random
from collections.abc import AsyncIterator, Awaitable, Callable
from contextlib import AsyncExitStack, asynccontextmanager
from contextvars import ContextVar
from datetime import datetime, timezone
from email.utils import parsedate_to_datetime
from functools import partial
from typing import Any, Literal, TypeVar

from niagads.common.core import ComponentBaseMixin
from niagads.common.models.base import CustomBaseModel
from pydantic import Field
from pydantic_ai import RunContext
from pydantic_ai.exceptions import ModelAPIError, ModelHTTPError
from pydantic_ai.messages import ModelMessage, ModelResponse
from pydantic_ai.models import Model, ModelRequestParameters, StreamedResponse
from pydantic_ai.models.wrapper import WrapperModel
from pydantic_ai.settings import ModelSettings


class RetryStatus(CustomBaseModel):
    """Transient model progress independent of presentation components."""

    state: Literal["requesting", "waiting", "retrying", "failed"]
    attempt: int = Field(ge=1, le=5)
    wait_seconds: float = Field(default=0, ge=0, serialization_alias="waitSeconds")


StatusCallback = Callable[[RetryStatus | None], None]
retry_status_callback: ContextVar[StatusCallback | None] = ContextVar(
    "ask_retry_status", default=None
)
retry_deadline: ContextVar[asyncio.Timeout | None] = ContextVar(
    "ask_retry_deadline", default=None
)
retry_after_header: ContextVar[str | None] = ContextVar("ask_retry_after", default=None)
T = TypeVar("T")


async def _capture_retry_after(response):
    retry_after_header.set(response.headers.get("retry-after"))


def configure_retry_client(client) -> None:
    """Keep one retry policy and retain headers the SDK drops on body errors."""
    client.max_retries = 0
    # OpenAI exposes no response hook; use its pinned HTTP client's hook API.
    client._client.event_hooks["response"].append(_capture_retry_after)


def _failure_details(error: Exception) -> tuple[int | None, str | None]:
    """Read native HTTP status or an OpenRouter error envelope, never message text."""
    if not isinstance(error, (ModelAPIError, ModelHTTPError)):
        return None, None
    status = getattr(error, "status_code", None)
    retry_after = None
    current = error
    while current is not None:
        headers = getattr(current, "headers", None)
        if headers is None:
            headers = getattr(getattr(current, "response", None), "headers", {})
        retry_after = (
            retry_after or headers.get("retry-after") or headers.get("Retry-After")
        )
        body = getattr(current, "body", None)
        if status is None and isinstance(body, dict):
            envelope = body.get("error", body)
            if isinstance(envelope, dict):
                code = envelope.get("code")
                if isinstance(code, int) or isinstance(code, str) and code.isdecimal():
                    status = int(code)
        current = current.__cause__
    return status, retry_after


def _wait_seconds(header: str | None, fallback: float) -> float:
    if header is not None:
        try:
            seconds = float(header)
            if 0 <= seconds < float("inf"):
                return seconds
        except ValueError:
            try:
                date = parsedate_to_datetime(header)
                return max(0, (date - datetime.now(timezone.utc)).total_seconds())
            except (TypeError, ValueError, OverflowError):
                pass
    return fallback


async def call_with_retry(
    call: Callable[[], Awaitable[T]], *, on_status: StatusCallback | None = None
) -> T:
    """Retry only 429/5xx, preserving the final native exception and cancellation."""
    callback = on_status or retry_status_callback.get()
    delays = (5, 15, 30, 60)
    for attempt in range(1, 6):
        if callback:
            callback(
                RetryStatus(
                    state="requesting" if attempt == 1 else "retrying", attempt=attempt
                )
            )
        header_token = retry_after_header.set(None)
        try:
            response = await call()
        except Exception as error:
            status, header = _failure_details(error)
            header = header or retry_after_header.get()
            if status != 429 and not (status is not None and 500 <= status <= 599):
                if callback:
                    callback(None)
                raise
            if attempt == 5:
                if callback:
                    callback(RetryStatus(state="failed", attempt=attempt))
                raise
            delay = _wait_seconds(header, delays[attempt - 1] + random.uniform(0, 1))
            logging.getLogger("uvicorn.error.niagads.ask").info(
                "OpenRouter retry attempt=%s/5 status=%s wait=%.2fs",
                attempt + 1,
                status,
                delay,
            )
            if callback:
                callback(
                    RetryStatus(
                        state="waiting", attempt=attempt + 1, wait_seconds=delay
                    )
                )
            deadline = retry_deadline.get()
            when = deadline.when() if deadline else None
            started = asyncio.get_running_loop().time()
            if deadline and when is not None:
                deadline.reschedule(None)
            try:
                await asyncio.sleep(delay)
            finally:
                if deadline and when is not None:
                    deadline.reschedule(
                        when + asyncio.get_running_loop().time() - started
                    )
        else:
            if callback:
                callback(None)
            return response
        finally:
            retry_after_header.reset(header_token)


class RetryingModel(WrapperModel, ComponentBaseMixin):
    """Share one retry helper across model requests and evidence streaming."""

    def __init__(self, model: Model):
        ComponentBaseMixin.__init__(self)
        WrapperModel.__init__(self, model)

    async def request(
        self,
        messages: list[ModelMessage],
        model_settings: ModelSettings | None,
        model_request_parameters: ModelRequestParameters,
    ) -> ModelResponse:
        return await call_with_retry(
            partial(
                self.wrapped.request, messages, model_settings, model_request_parameters
            )
        )

    @asynccontextmanager
    async def request_stream(
        self,
        messages: list[ModelMessage],
        model_settings: ModelSettings | None,
        model_request_parameters: ModelRequestParameters,
        run_context: RunContext[Any] | None = None,
    ) -> AsyncIterator[StreamedResponse]:
        async with AsyncExitStack() as stack:
            response = await call_with_retry(
                lambda: stack.enter_async_context(
                    self.wrapped.request_stream(
                        messages, model_settings, model_request_parameters, run_context
                    )
                )
            )
            # Once a response is delivered, never replay partial text or tool calls.
            yield response
