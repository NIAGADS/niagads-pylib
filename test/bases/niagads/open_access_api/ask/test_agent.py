"""The agent runs real tools against mocked API responses."""

import asyncio

import httpx
from niagads.open_access_api.ask.agent import build_agent
from niagads.open_access_api.ask.config import AskSettings
from niagads.open_access_api.ask.results import ResultStore
from pydantic_ai.messages import ModelResponse, TextPart, ToolCallPart
from pydantic_ai.models.function import FunctionModel


def test_agent_retrieves_and_presents_server_owned_result():
    calls = []

    def model(messages, info):
        calls.append(messages)
        if len(calls) == 1:
            return ModelResponse(
                parts=[ToolCallPart("get_track", {"track": "track-1"})]
            )
        if len(calls) == 2:
            result_id = next(iter(store.results))
            return ModelResponse(
                parts=[
                    ToolCallPart(
                        "present_results",
                        {"result_id": result_id, "component": "table"},
                    )
                ]
            )
        return ModelResponse(
            parts=[TextPart("One matching test track; source track-1.")]
        )

    store = ResultStore()

    async def run():
        async with httpx.AsyncClient(
            transport=httpx.MockTransport(
                lambda _: httpx.Response(
                    200, json={"data": [{"id": "track-1", "label": "Test track"}]}
                )
            ),
            base_url="http://api",
        ) as client:
            agent = build_agent(AskSettings(), model=FunctionModel(model))
            return await agent.run(
                "Get track-1", deps={"store": store, "client": client, "spec": {}}
            )

    result = asyncio.run(run())
    assert "track-1" in result.output
    assert len(store.results) == 1
    assert store.presentations[0].component == "table"
    assert store.get(store.presentations[0].result_id).rows[0]["id"] == "track-1"
