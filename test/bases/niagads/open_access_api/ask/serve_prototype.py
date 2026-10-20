"""Test-only browser harness: existing API app, synthetic API data, fake model.

Run with PYTHONPATH=components:bases. This never connects to a database or LLM.
It must not be deployed as an application service.
"""

import importlib
import json
import os
from contextlib import asynccontextmanager

import httpx
import uvicorn
from niagads.open_access_api.ask.agent import build_agent
from niagads.open_access_api.ask.config import AskSettings
from niagads.open_access_api.ask.transport import get_agent, get_api_transport
from pydantic_ai.messages import ModelRequest, ToolReturnPart, UserPromptPart
from pydantic_ai.models.function import DeltaToolCall, FunctionModel


def mock_api(request):
    """Synthetic test identifiers are intentionally unrelated to real records."""
    if request.url.path.endswith("/structure"):
        return httpx.Response(
            200,
            json={
                "data": [
                    {
                        "transcripts": [
                            {
                                "id": "TEST-TRANSCRIPT",
                                "location": "chr1:100-200",
                            },
                        ]
                    }
                ]
            },
        )
    if request.url.path == "/record/region/associations":
        return httpx.Response(501, json={"detail": "ORM integration pending"})
    if request.url.path.endswith("/associations"):
        if request.url.params.get("content") == "summary":
            return httpx.Response(
                200,
                json={
                    "data": [
                        {
                            "track": "test-track-a",
                            "traits": {},
                            "num_associations": 1200,
                        },
                        {
                            "track": "test-track-b",
                            "traits": {},
                            "num_associations": 35,
                        },
                    ]
                },
            )
        return httpx.Response(
            200,
            json={
                "data": [
                    {
                        "variant": "test-variant-1",
                        "track": "test-track-a",
                        "pvalue": "0.001",
                    },
                    {
                        "variant": "test-variant-2",
                        "track": "test-track-a",
                        "pvalue": "0.002",
                    },
                    {
                        "variant": "test-variant-3",
                        "track": "test-track-b",
                        "pvalue": "0.003",
                    },
                ]
            },
        )
    return httpx.Response(
        200,
        json={
            "data": [
                {
                    "id": "test-gene",
                    "label": "Synthetic test gene",
                },
            ]
        },
    )


async def mock_model(messages, info):
    """A deterministic fake model exercises the real registered tool functions."""
    returns = [
        part
        for message in messages
        if isinstance(message, ModelRequest)
        for part in message.parts
        if isinstance(part, ToolReturnPart)
    ]
    question = next(
        (
            part.content
            for message in reversed(messages)
            if isinstance(message, ModelRequest)
            for part in message.parts
            if isinstance(part, UserPromptPart)
            and isinstance(part.content, str)
        ),
        "",
    )
    if not returns:
        if "transcript" in question.casefold():
            name, args = "get_transcript_associations", {
                "gene": "test-gene",
                "transcript": "TEST-TRANSCRIPT",
            }
        elif "phenotype" in question.casefold():
            name, args = "find_phenotype_genes", {
                "phenotype": "test-phenotype"
            }
        elif "dashboard" in question.casefold():
            name, args = "get_gene_associations", {
                "gene": "test-gene",
                "content": "summary",
            }
        else:
            name, args = "get_gene", {"gene": "test-gene"}
        yield {
            0: DeltaToolCall(
                name=name,
                json_args=json.dumps(args),
                tool_call_id="test-fetch",
            )
        }
    elif (
        len(returns) == 1
        and isinstance(returns[0].content, dict)
        and "result_id" in returns[0].content
    ):
        result_id = returns[0].content["result_id"]
        calls = {
            0: DeltaToolCall(
                name="present_results",
                json_args=json.dumps(
                    {"result_id": result_id, "component": "table"}
                ),
                tool_call_id="test-table",
            ),
        }
        if returns[0].content.get("content") == "summary":
            calls[1] = DeltaToolCall(
                name="present_results",
                json_args=json.dumps(
                    {
                        "result_id": result_id,
                        "component": "association_source_bar",
                    }
                ),
                tool_call_id="test-chart",
            )
        yield calls
    else:
        yield "MOCK DATA: this response exercises the prototype with synthetic records. "
        yield "Region and phenotype retrieval require the deferred ORM integration."


@asynccontextmanager
async def no_database_lifespan(app):
    """Test harness startup deliberately bypasses live database initialization."""
    yield


def main():
    """Import the existing production application without running its lifespan."""
    os.environ["DATABASE_URI"] = (
        "postgresql://prototype:prototype@127.0.0.1/prototype"
    )
    os.environ["CACHE_DB_URI"] = "redis://127.0.0.1:6379/0"
    os.environ["ASK_TELEMETRY"] = "false"
    app = importlib.import_module("niagads.open_access_api.app").app
    app.router.lifespan_context = no_database_lifespan
    app.dependency_overrides[get_agent] = lambda: build_agent(
        AskSettings(), model=FunctionModel(stream_function=mock_model)
    )
    app.dependency_overrides[get_api_transport] = lambda: httpx.MockTransport(
        mock_api
    )
    uvicorn.run(app, host="127.0.0.1", port=8010)


if __name__ == "__main__":
    main()
