"""Token recovery through the real SDK; recorded records and protocol-only failures."""

import asyncio
import json
from pathlib import Path

import httpx
import pytest
from fastapi import FastAPI
from niagads.api.common.types import AnnotationKind
from niagads.common.types import Entity
from niagads.open_access_api.ask import tools, transport
from niagads.open_access_api.ask.agent import build_agent
from niagads.open_access_api.ask.config import AskSettings
from niagads.open_access_api.ask.contracts import ResultSet
from pydantic_ai.models.function import DeltaToolCall, FunctionModel


@pytest.mark.parametrize(
    "stage",
    ["before_retrieval", "input", "output", "presentation", "requests", "other"],
)
def test_interrupted_stream_preserves_records_and_native_diagnostics(
    stage, monkeypatch
):
    path = Path(__file__).parents[1] / "data" / "gene_record_mapping_response.json"
    rows = json.loads(path.read_text())["data"]["APOE"]
    retrieved = ResultSet(
        entity=Entity.GENE,
        annotation=AnnotationKind.REPORT,
        rows=rows,
        parameters={"gene": "APOE"},
        sources=[rows[0]["id"]],
    )
    calls = []
    run = {}

    native_stream = transport.VercelAIAdapter.run_stream_native

    def start_run(adapter, *, usage, usage_limits, **kwargs):
        run.update(usage=usage, limits=usage_limits)
        return native_stream(adapter, usage=usage, usage_limits=usage_limits, **kwargs)

    async def retrieve(*args):
        return retrieved

    async def protocol(messages, info):
        calls.append(messages)
        if stage == "before_retrieval":
            usage, limits = run["usage"], run["limits"]
            usage.input_tokens = limits.input_tokens_limit + 1
            limits.check_tokens(usage)
        if len(calls) == 1:
            yield {
                0: DeltaToolCall(
                    name="get_gene", json_args='{"gene":"APOE"}', tool_call_id="record"
                )
            }
            return
        if stage == "presentation" and len(calls) == 2:
            yield {
                0: DeltaToolCall(
                    name="present_results",
                    json_args=json.dumps(
                        {"presentation": {"result_id": retrieved.id, "view": "auto"}}
                    ),
                    tool_call_id="view",
                )
            }
            return
        # A partial narrative must be closed cleanly before the recovery message.
        yield "Retrieval completed."
        usage, limits = run["usage"], run["limits"]
        if stage in {"input", "presentation"}:
            usage.input_tokens = limits.input_tokens_limit + 1
            limits.check_tokens(usage)
        elif stage == "output":
            usage.output_tokens = limits.output_tokens_limit + 1
            limits.check_tokens(usage)
        elif stage == "requests":
            usage.requests = limits.request_limit
            limits.check_before_request(usage)
        else:
            raise RuntimeError("Native protocol failure")

    settings = AskSettings(feedback_enable=False)
    agent = build_agent(settings, model=FunctionModel(stream_function=protocol))
    app = FastAPI()
    app.include_router(transport.router)
    app.dependency_overrides[transport.get_agent] = lambda: agent
    app.dependency_overrides[transport.get_settings] = lambda: settings
    monkeypatch.setattr(transport.VercelAIAdapter, "run_stream_native", start_run)
    monkeypatch.setattr(tools, "retrieve", retrieve)

    async def request():
        async with httpx.AsyncClient(
            transport=httpx.ASGITransport(app=app), base_url="http://test"
        ) as client:
            return await client.post(
                "/ask",
                json={
                    "messages": [
                        {
                            "role": "user",
                            "parts": [{"type": "text", "text": "Retrieve APOE"}],
                        }
                    ]
                },
            )

    response = asyncio.run(request())
    assert response.status_code == 200
    assert response.text.rstrip().endswith("data: [DONE]")
    events = [
        json.loads(line[6:])
        for line in response.text.splitlines()
        if line.startswith("data: {")
    ]
    envelopes = [
        event["data"] for event in events if event["type"] == "data-niagads-result"
    ]
    assert len(envelopes) == 1
    envelope = envelopes[0]
    assert envelope["results"] == (
        [] if stage == "before_retrieval" else [retrieved.model_dump(mode="json")]
    )
    assert len(calls) == (
        1 if stage == "before_retrieval" else 3 if stage == "presentation" else 2
    )
    if stage == "presentation":
        assert envelope["presentation"][0]["result_id"] == retrieved.id
    errors = [event for event in events if event["type"] == "error"]
    if stage in {"requests", "other"}:
        assert envelope["status"] == "retrieval_error"
        assert errors
        expected_error = (
            "request_limit" if stage == "requests" else "Native protocol failure"
        )
        assert expected_error in errors[0]["errorText"]
        return
    assert envelope["status"] == "token_limit"
    assert not errors
    assert envelope["issues"][0]["code"] == "usage_limit"
    assert envelope["issues"][0]["request_id"]
    assert "tokens_limit" in envelope["issues"][0]["message"]
    text = "".join(event["delta"] for event in events if event["type"] == "text-delta")
    assert "Token limit reached before I finished" in text
    assert "narrow" in text.lower()
    assert ("No records" if stage == "before_retrieval" else "1 loaded record") in text
    assert len([event for event in events if event["type"] == "start"]) == 1
    assert [event for event in events if event["type"] == "finish"][-1][
        "finishReason"
    ] == "length"
    assert {event["id"] for event in events if event["type"] == "text-start"} == {
        event["id"] for event in events if event["type"] == "text-end"
    }
