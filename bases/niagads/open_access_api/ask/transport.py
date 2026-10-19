"""AI SDK streaming route on the existing application, with bounded input."""

import asyncio
import json
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
                raise ValueError("Conversation context exceeds prototype limit")
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
        raise HTTPException(
            503, "Invalid assistant configuration; configure an explicit free model."
        ) from exc


def get_agent(settings: AskSettings = Depends(get_settings)):
    """Provide an injectable model agent; configuration errors are actionable."""
    try:
        return build_agent(settings)
    except ValueError as exc:
        raise HTTPException(503, str(exc)) from exc


def get_api_transport(request: Request) -> httpx.AsyncBaseTransport:
    """Reuse this application's registered API routes, preserving its boundaries."""
    return httpx.ASGITransport(app=request.app)


@router.post("/ask", summary="Ask NIAGADS (prototype)", operation_id="askNiagads")
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
            raise HTTPException(413, "Conversation request exceeds 64 KiB")
    try:
        payload = json.loads(raw)
        if not isinstance(payload, dict):
            raise ValueError("Expected a conversation object")
        clean = sanitize_history(payload)
        run_input = VercelAIAdapter.build_run_input(json.dumps(clean).encode())
    except (ValueError, TypeError) as exc:
        raise HTTPException(422, "Invalid conversation: " + str(exc)) from exc
    adapter = VercelAIAdapter(agent=agent, run_input=run_input, sdk_version=7)
    store = ResultStore()
    # API help needs registered operations, not unrelated application server metadata.
    spec = get_openapi(
        title="ASK NIAGADS operation catalog",
        version="prototype",
        routes=request.app.routes,
    )
    deps = {"store": store, "spec": spec, "warnings": [], "failures": []}

    async def complete(result):
        presentations = store.presentations or [
            Presentation(component="table", result_id=r.id)
            for r in list(store.results.values())[:6]
        ]
        status = (
            deps["failures"][0]
            if deps["failures"]
            else (
                "empty"
                if store.results and not any(r.rows for r in store.results.values())
                else "ok"
            )
        )
        envelope = AskResponse(
            status=status,
            results=list(store.results.values()),
            presentation=presentations,
            warnings=deps["warnings"],
        )
        yield DataChunk(
            type="data-niagads-result", data=envelope.model_dump(mode="json")
        )

    async def stream():
        headers = {
            name: request.headers[name]
            for name in ("authorization", "cookie", "x-request-id")
            if name in request.headers
        }
        try:
            async with asyncio.timeout(settings.deadline):
                async with httpx.AsyncClient(
                    transport=transport,
                    base_url="http://niagads.internal",
                    headers=headers,
                    timeout=settings.api_timeout,
                ) as client:
                    deps["client"] = client
                    events = adapter.run_stream(
                        deps=deps,
                        on_complete=complete,
                        usage_limits=UsageLimits(
                            request_limit=settings.model_requests,
                            tool_calls_limit=settings.tool_calls,
                            input_tokens_limit=20000,
                            output_tokens_limit=12000,
                        ),
                    )

                    async def safe_events():
                        async for event in events:
                            if isinstance(event, ErrorChunk):
                                yield ErrorChunk(
                                    errorText="Assistant provider or tool failed. Retry or narrow the question."
                                )
                            else:
                                yield event

                    async for event in adapter.encode_stream(safe_events()):
                        yield event
        except asyncio.CancelledError:
            raise
        except Exception:
            # Never expose upstream credentials, raw provider bodies, or stack traces.
            yield 'data: {"type":"error","errorText":"Assistant request failed or reached its limit. Retry or narrow the question."}\n\n'
            yield "data: [DONE]\n\n"

    return StreamingResponse(
        stream(),
        media_type="text/event-stream",
        headers={"x-vercel-ai-ui-message-stream": "v1", "Cache-Control": "no-cache"},
    )
