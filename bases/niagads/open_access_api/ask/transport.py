"""AI SDK streaming route on the existing application, with bounded input."""

import asyncio
import json
import logging
from contextlib import nullcontext
from uuid import uuid4

import httpx
import logfire
from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.openapi.utils import get_openapi
from niagads.open_access_api.ask.agent import build_agent
from niagads.open_access_api.ask.config import AskSettings
from niagads.open_access_api.ask.contracts import AskIssue, AskResponse
from niagads.open_access_api.ask.feedback import (
    AskFeedback,
    create_feedback_reference,
    record_feedback,
)
from niagads.open_access_api.ask.planning import QueryPlan
from niagads.open_access_api.ask.results import ResultStore
from niagads.open_access_api.ask.retries import (
    RetryStatus,
    retry_deadline,
    retry_status_callback,
)
from pydantic_ai.exceptions import UsageLimitExceeded
from pydantic_ai.ui.vercel_ai import VercelAIAdapter
from pydantic_ai.ui.vercel_ai.response_types import (
    DataChunk,
    ErrorChunk,
    FinishChunk,
    StartChunk,
    TextDeltaChunk,
    TextEndChunk,
    TextStartChunk,
)
from pydantic_ai.usage import RunUsage, UsageLimits
from starlette.responses import Response, StreamingResponse

router = APIRouter(tags=["ASK NIAGADS"])


def token_limit_exceeded(
    error: Exception, usage: RunUsage, limits: UsageLimits
) -> bool:
    """Recognize native SDK token exhaustion without relabeling other usage errors."""
    return isinstance(error, UsageLimitExceeded) and any(
        limit is not None and consumed > limit
        for consumed, limit in (
            (usage.input_tokens, limits.input_tokens_limit),
            (usage.output_tokens, limits.output_tokens_limit),
            (usage.total_tokens, limits.total_tokens_limit),
        )
    )


def sanitize_history(payload: dict) -> dict:
    """Accept bounded text history only; client tool outputs are never evidence."""
    messages = payload.get("messages")
    if not isinstance(messages, list) or not 1 <= len(messages) <= 12:
        raise ValueError("Supply 1 to 12 conversation messages")
    clean = []
    size = 0
    for message in messages:
        if not isinstance(message, dict) or message.get("role") not in {
            "user",
            "assistant",
        }:
            raise ValueError("Only user and assistant text history is accepted")
        parts = message.get("parts", [])
        if not isinstance(parts, list):
            raise ValueError("Message parts must be a list")
        texts = []
        for part in parts:
            if not isinstance(part, dict):
                raise ValueError("Invalid message part")
            if part.get("type") != "text":
                if message["role"] == "user":
                    raise ValueError("Only text queries are supported")
                continue
            text = part.get("text")
            if not isinstance(text, str):
                raise ValueError("Message text must be a string")
            size += len(text)
            if len(text) > 8000 or size > 16000:
                raise HTTPException(
                    413,
                    "This conversation is too long. "
                    "Start a new session with a shorter question.",
                )
            texts.append({"type": "text", "text": text})
        if texts:
            clean.append({"id": str(uuid4()), "role": message["role"], "parts": texts})
    if not clean or clean[-1]["role"] != "user":
        raise ValueError("The final message must contain a user question")
    return {"id": str(uuid4()), "messages": clean, "trigger": "submit-message"}


def get_settings() -> AskSettings:
    """Load optional assistant configuration without changing existing API settings."""
    try:
        return AskSettings()
    except ValueError as exc:
        raise RuntimeError(
            f"ASK configuration failed: {type(exc).__name__}: {exc}"
        ) from exc


def get_agent(settings: AskSettings = Depends(get_settings)):
    """Provide an injectable model agent; configuration errors are actionable."""
    try:
        return build_agent(settings)
    except ValueError as exc:
        raise RuntimeError(
            f"ASK agent initialization failed: {type(exc).__name__}: {exc}"
        ) from exc


def get_api_transport(request: Request) -> httpx.AsyncBaseTransport:
    """Reuse this application's registered API routes, preserving its boundaries."""
    return httpx.ASGITransport(app=request.app)


@router.post("/ask/feedback", status_code=204, operation_id="submitAskFeedback")
async def submit_feedback(
    feedback: AskFeedback,
    request: Request,
    settings: AskSettings = Depends(get_settings),
) -> Response:
    secret = getattr(request.app.state, "ask_feedback_signing_secret", None)
    if (
        not getattr(request.app.state, "ask_telemetry_enabled", False)
        or not settings.feedback_enable
        or secret is None
    ):
        raise HTTPException(503, "Feedback is currently unavailable")
    try:
        record_feedback(feedback, secret)
    except ValueError as exc:
        raise HTTPException(422, "Invalid feedback reference") from exc
    return Response(status_code=204)


@router.post(
    "/ask",
    summary="Ask NIAGADS",
    operation_id="askNiagads",
    openapi_extra={"x-status": "alpha"},
)
async def ask(
    request: Request,
    agent=Depends(get_agent),
    transport=Depends(get_api_transport),
    settings: AskSettings = Depends(get_settings),
) -> StreamingResponse:
    """Stream grounded text and complete result parts; no database code lives here."""
    raw = bytearray()
    async for chunk in request.stream():
        raw.extend(chunk)
        if len(raw) > 65536:
            raise HTTPException(
                413, "The conversation is too long. Start a new session."
            )
    try:
        payload = json.loads(raw)
        if not isinstance(payload, dict):
            raise ValueError("Expected a conversation object")
        clean = sanitize_history(payload)
        run_input = VercelAIAdapter.build_run_input(json.dumps(clean).encode())
    except (ValueError, TypeError) as exc:
        raise HTTPException(
            422,
            f"Invalid conversation: {type(exc).__name__}: {exc}",
        ) from exc
    adapter = VercelAIAdapter(agent=agent, run_input=run_input, sdk_version=7)
    store = ResultStore()
    # API help needs registered operations, not unrelated application server metadata.
    spec = get_openapi(
        title="ASK NIAGADS operation catalog",
        version="prototype",
        routes=request.app.routes,
    )
    deps = {"store": store, "spec": spec, "warnings": [], "failures": [], "issues": []}

    result_sent = False
    token_limit_error: UsageLimitExceeded | None = None
    feedback_reference = None
    feedback_secret = getattr(request.app.state, "ask_feedback_signing_secret", None)
    feedback_enabled = bool(
        getattr(request.app.state, "ask_telemetry_enabled", False)
        and settings.feedback_enable
        and feedback_secret is not None
    )

    async def complete(result, failed: bool = False):
        nonlocal result_sent
        if result_sent:
            return
        if token_limit_error is not None:
            status = "token_limit"
        elif failed:
            status = "retrieval_error"
        elif deps["failures"]:
            status = deps["failures"][0]
        elif store.results and not any(
            result.rows for result in store.results.values()
        ):
            status = "empty"
        else:
            status = "ok"
        envelope = AskResponse(
            feedback_reference=feedback_reference,
            status=status,
            results=list(store.results.values()),
            presentation=store.presentations,
            warnings=list(dict.fromkeys(deps["warnings"])),
            issues=list(
                {issue.model_dump_json(): issue for issue in deps["issues"]}.values()
            ),
        )
        result_sent = True
        yield DataChunk(
            type="data-niagads-result", data=envelope.model_dump(mode="json")
        )

    async def generate_stream():
        nonlocal feedback_reference, token_limit_error
        message_started = False
        headers = {
            name: request.headers[name]
            for name in ("authorization", "cookie", "x-request-id")
            if name in request.headers
        }
        headers.setdefault("x-request-id", str(uuid4()))
        usage = RunUsage()
        usage_limits = UsageLimits(
            request_limit=settings.model_requests,
            tool_calls_limit=settings.tool_calls,
            input_tokens_limit=20000,
            output_tokens_limit=12000,
        )

        async def recover_token_limit():
            nonlocal message_started
            deps["issues"].append(
                AskIssue(
                    code="usage_limit",
                    operation="assistant",
                    message=f"{type(token_limit_error).__name__}: {token_limit_error}",
                    request_id=headers["x-request-id"],
                )
            )
            if not message_started:
                yield StartChunk(message_id=str(uuid4()))
                message_started = True
            count = sum(len(result.rows) for result in store.results.values())
            retrieved = (
                f"{count} loaded record{'s have' if count != 1 else ' has'} been preserved."
                if count
                else "No records were retrieved."
            )
            text_id = str(uuid4())
            yield TextStartChunk(id=text_id)
            yield TextDeltaChunk(
                id=text_id,
                delta=(
                    "\n\nToken limit reached before I finished. "
                    f"{retrieved} Would you like to narrow the request "
                    "to one gene, dataset or region?"
                ),
            )
            yield TextEndChunk(id=text_id)
            async for event in complete(None):
                yield event

        with (
            logfire.span("ASK NIAGADS response") if feedback_enabled else nullcontext()
        ):
            if feedback_enabled:
                feedback_reference = create_feedback_reference(feedback_secret)
            try:
                async with asyncio.timeout(settings.deadline) as deadline:
                    retry_deadline.set(deadline)
                    async with httpx.AsyncClient(
                        transport=transport,
                        base_url="http://niagads.internal",
                        headers=headers,
                        timeout=settings.api_timeout,
                    ) as client:
                        deps["client"] = client
                        native_events = adapter.run_stream_native(
                            deps=deps,
                            usage=usage,
                            usage_limits=usage_limits,
                        )

                        async def observed_events():
                            nonlocal token_limit_error
                            try:
                                async for event in native_events:
                                    yield event
                            except Exception as exc:
                                if token_limit_exceeded(exc, usage, usage_limits):
                                    token_limit_error = exc
                                logging.getLogger(
                                    "uvicorn.error.niagads.ask"
                                ).exception(
                                    "ASK stream failed request_id=%s",
                                    headers["x-request-id"],
                                )
                                raise

                        events = adapter.transform_stream(
                            observed_events(), on_complete=complete
                        )

                        async def stream_events():
                            nonlocal message_started
                            async for event in events:
                                if isinstance(event, StartChunk):
                                    message_started = True
                                if isinstance(event, ErrorChunk):
                                    if token_limit_error is not None:
                                        async for recovered in recover_token_limit():
                                            yield recovered
                                        continue
                                    if not message_started and feedback_reference:
                                        yield StartChunk(message_id=str(uuid4()))
                                        message_started = True
                                    if store.results or feedback_reference:
                                        async for result_event in complete(
                                            None, failed=True
                                        ):
                                            yield result_event
                                    event.error_text += (
                                        f" Reference: {headers['x-request-id']}."
                                    )
                                if (
                                    isinstance(event, FinishChunk)
                                    and token_limit_error is not None
                                ):
                                    event = event.model_copy(
                                        update={"finish_reason": "length"}
                                    )
                                yield event

                        async for event in adapter.encode_stream(stream_events()):
                            yield event
            except asyncio.CancelledError:
                raise
            except Exception as exc:
                logging.getLogger("uvicorn.error.niagads.ask").exception(
                    "ASK stream failed request_id=%s", headers["x-request-id"]
                )
                if token_limit_exceeded(exc, usage, usage_limits):
                    token_limit_error = exc
                    async for event in recover_token_limit():
                        yield "data: " + event.encode(7) + "\n\n"
                    event = FinishChunk(finish_reason="length")
                    yield "data: " + event.encode(7) + "\n\n"
                    yield "data: [DONE]\n\n"
                    return
                if not message_started and feedback_reference:
                    event = StartChunk(message_id=str(uuid4()))
                    yield "data: " + event.encode(sdk_version=7) + "\n\n"
                if store.results or feedback_reference:
                    async for event in complete(None, failed=True):
                        yield "data: " + event.encode(sdk_version=7) + "\n\n"
                event = ErrorChunk(
                    errorText=(
                        f"{type(exc).__name__}: {exc} "
                        f"Reference: {headers['x-request-id']}."
                    )
                )
                yield "data: " + event.encode(sdk_version=7) + "\n\n"
                yield "data: [DONE]\n\n"

    async def stream():
        # Relay tool data and retry status while native execution is in progress.
        queue: asyncio.Queue[str | Exception | None] = asyncio.Queue()

        def report_status(status: RetryStatus | None):
            # DataChunk.encode excludes None; clearing needs an explicit JSON null.
            event = {
                "type": "data-niagads-model-status",
                "data": (
                    status.model_dump(mode="json", by_alias=True) if status else None
                ),
                "transient": True,
            }
            queue.put_nowait("data: " + json.dumps(event) + "\n\n")

        def report_plan(interpretation: QueryPlan):
            event = DataChunk(
                type="data-niagads-plan", data=interpretation.model_dump(mode="json")
            )
            queue.put_nowait("data: " + event.encode(sdk_version=7) + "\n\n")

        deps["report_plan"] = report_plan

        async def produce():
            status_token = retry_status_callback.set(report_status)
            deadline_token = retry_deadline.set(None)
            try:
                async for chunk in generate_stream():
                    await queue.put(chunk)
            except Exception as error:
                await queue.put(error)
            finally:
                retry_status_callback.reset(status_token)
                retry_deadline.reset(deadline_token)
                queue.put_nowait(None)

        producer = asyncio.create_task(produce())
        try:
            while True:
                try:
                    chunk = await asyncio.wait_for(queue.get(), timeout=15)
                except TimeoutError:
                    yield ": keep-alive\n\n"
                    continue
                if chunk is None:
                    break
                if isinstance(chunk, Exception):
                    raise chunk
                yield chunk
        finally:
            producer.cancel()
            await asyncio.gather(producer, return_exceptions=True)

    return StreamingResponse(
        stream(),
        media_type="text/event-stream",
        headers={"x-vercel-ai-ui-message-stream": "v1", "Cache-Control": "no-cache"},
    )
