"""AI SDK streaming route on the existing application, with bounded input."""

import asyncio
import json
import logging
from uuid import uuid4

import httpx
from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.openapi.utils import get_openapi
from niagads.open_access_api.ask.agent import build_agent
from niagads.open_access_api.ask.config import AskSettings
from niagads.open_access_api.ask.contracts import AskResponse, Presentation
from niagads.open_access_api.ask.results import ResultStore
from pydantic_ai.ui.vercel_ai import VercelAIAdapter
from pydantic_ai.ui.vercel_ai.response_types import DataChunk, ErrorChunk
from pydantic_ai.usage import UsageLimits
from starlette.responses import StreamingResponse

router = APIRouter(tags=["ASK NIAGADS"])


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

    async def complete(result, failed: bool = False):
        nonlocal result_sent
        if result_sent:
            return
        presentations = store.presentations or [
            Presentation(component="table", result_id=r.id)
            for r in list(store.results.values())[:6]
        ]
        status = (
            "retrieval_error"
            if failed
            else (
                deps["failures"][0]
                if deps["failures"]
                else (
                    "empty"
                    if store.results and not any(r.rows for r in store.results.values())
                    else "ok"
                )
            )
        )
        envelope = AskResponse(
            status=status,
            results=list(store.results.values()),
            presentation=presentations,
            warnings=list(dict.fromkeys(deps["warnings"])),
            issues=list(
                {issue.model_dump_json(): issue for issue in deps["issues"]}.values()
            ),
        )
        result_sent = True
        yield DataChunk(
            type="data-niagads-result", data=envelope.model_dump(mode="json")
        )

    async def stream():
        headers = {
            name: request.headers[name]
            for name in ("authorization", "cookie", "x-request-id")
            if name in request.headers
        }
        headers.setdefault("x-request-id", str(uuid4()))
        try:
            async with asyncio.timeout(settings.deadline):
                async with httpx.AsyncClient(
                    transport=transport,
                    base_url="http://niagads.internal",
                    headers=headers,
                    timeout=settings.api_timeout,
                ) as client:
                    deps["client"] = client
                    native_events = adapter.run_stream_native(
                        deps=deps,
                        usage_limits=UsageLimits(
                            request_limit=settings.model_requests,
                            tool_calls_limit=settings.tool_calls,
                            input_tokens_limit=20000,
                            output_tokens_limit=12000,
                        ),
                    )

                    async def observed_events():
                        try:
                            async for event in native_events:
                                yield event
                        except Exception:
                            logging.getLogger("uvicorn.error.niagads.ask").exception(
                                "ASK stream failed request_id=%s",
                                headers["x-request-id"],
                            )
                            raise

                    events = adapter.transform_stream(
                        observed_events(), on_complete=complete
                    )

                    async def stream_events():
                        async for event in events:
                            if isinstance(event, ErrorChunk):
                                if store.results:
                                    async for result_event in complete(
                                        None, failed=True
                                    ):
                                        yield result_event
                                event.error_text += (
                                    f" Reference: {headers['x-request-id']}."
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
            if store.results:
                async for event in complete(None, failed=True):
                    yield "data: " + event.model_dump_json(by_alias=True) + "\n\n"
            event = ErrorChunk(
                errorText=(
                    f"{type(exc).__name__}: {exc} "
                    f"Reference: {headers['x-request-id']}."
                )
            )
            yield "data: " + event.model_dump_json(by_alias=True) + "\n\n"
            yield "data: [DONE]\n\n"

    return StreamingResponse(
        stream(),
        media_type="text/event-stream",
        headers={"x-vercel-ai-ui-message-stream": "v1", "Cache-Control": "no-cache"},
    )
