"""Structured planning contracts and isolated SDK wiring; no live services."""

import asyncio
from types import SimpleNamespace

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from niagads.common.types import Entity
from niagads.open_access_api.ask.agent import build_agent
from niagads.open_access_api.ask.config import AskSettings
from niagads.open_access_api.ask.planning import QueryPlan, build_query_planner
from niagads.open_access_api.ask.tools import get_track_data, search_resources
from niagads.open_access_api.ask.transport import get_agent, get_settings, router
from pydantic import ValidationError
from pydantic_ai.exceptions import UnexpectedModelBehavior
from pydantic_ai.messages import ModelResponse, TextPart, ToolCallPart
from pydantic_ai.models.function import FunctionModel

EXAMPLES = [
    (
        "Find histone modifications in brain cells proximal to APOE. No cancer cells.",
        {
            "intent": "retrieve_data",
            "entity": "track",
            "selection": {
                "operator": "and",
                "operands": [
                    {"category": "annotation", "text": "histone modifications"},
                    {"category": "biosample", "text": "brain cells"},
                ],
            },
            "location": {"kind": "gene", "loc": "APOE"},
            "clarifications": [
                {"field": "location.flank_bp", "question": "How far around APOE?"}
            ],
            "exclusions": ["cancer cells"],
        },
    ),
    (
        "Find histone modifications in brain cells in chr19:100-200.",
        {
            "intent": "retrieve_data",
            "entity": "track",
            "selection": {
                "operator": "and",
                "operands": [
                    {"category": "annotation", "text": "histone modifications"},
                    {"category": "biosample", "text": "brain cells"},
                ],
            },
            "location": {"kind": "span", "loc": "chr19:100-200"},
        },
    ),
    (
        "Find Roadmap enhancers in the TREM2 region.",
        {
            "intent": "retrieve_data",
            "entity": "track",
            "selection": {
                "operator": "and",
                "operands": [
                    {"category": "source", "text": "Roadmap"},
                    {"category": "annotation", "text": "enhancers"},
                ],
            },
            "location": {"kind": "gene", "loc": "TREM2"},
        },
    ),
    (
        "Any GWAS with Korean and PSP participants?",
        {
            "intent": "discover_resources",
            "entity": "track",
            "selection": {
                "operator": "and",
                "operands": [
                    {"category": "assay", "text": "GWAS"},
                    {"category": "population", "text": "Korean"},
                    {"category": "phenotype", "text": "PSP"},
                ],
            },
            "clarifications": [
                {
                    "field": "selection",
                    "question": "Does PSP mean progressive supranuclear palsy?",
                }
            ],
        },
    ),
]


@pytest.mark.parametrize("question,payload", EXAMPLES)
def test_planner_returns_typed_research_plan(question, payload):
    def model(messages, info):
        assert not info.function_tools
        return ModelResponse(parts=[ToolCallPart(info.output_tools[0].name, payload)])

    result = asyncio.run(build_query_planner(FunctionModel(model)).run(question))
    assert result.output == QueryPlan.model_validate(payload)
    if result.output.location:
        assert result.output.location.flank_bp is None
        assert result.output.location.assembly is None


def test_boolean_grouping_preserves_population_alternatives():
    plan = QueryPlan.model_validate(
        {
            "intent": "discover_resources",
            "selection": {
                "operator": "and",
                "operands": [
                    {
                        "operator": "or",
                        "operands": [
                            {"category": "population", "text": "Korean"},
                            {"category": "population", "text": "Japanese"},
                        ],
                    },
                    {"category": "phenotype", "text": "PSP"},
                ],
            },
        }
    )
    assert plan.selection.operands[0].operator == "or"
    assert plan.selection.operands[1].text == "PSP"


@pytest.mark.parametrize(
    "extra",
    [
        {"endpoint": "https://untrusted.example"},
        {"selection": {"operator": "and", "operands": []}},
        {"location": {"kind": "gene", "loc": "APOE", "flank_bp": -1}},
    ],
)
def test_invalid_plans_fail_validation(extra):
    with pytest.raises(ValidationError):
        QueryPlan.model_validate({"intent": "discover_resources", **extra})


def test_invalid_llm_output_does_not_become_a_plan():
    def model(messages, info):
        return ModelResponse(
            parts=[ToolCallPart(info.output_tools[0].name, {"intent": "invented"})]
        )

    with pytest.raises(UnexpectedModelBehavior):
        asyncio.run(build_query_planner(FunctionModel(model)).run("Find datasets"))


@pytest.mark.parametrize(
    "constraint,status",
    [
        (
            {"clarifications": [{"field": "location", "question": "Which span?"}]},
            "clarification",
        ),
        ({"exclusions": ["cancer cells"]}, "unsupported"),
    ],
)
def test_unresolved_constraints_stop_api_retrieval(constraint, status):
    ctx = SimpleNamespace(
        deps={
            "query_plan": QueryPlan(intent="retrieve_data", **constraint),
            "failures": [],
            "issues": [],
        }
    )
    result = asyncio.run(search_resources(ctx, text="brain", entity=Entity.TRACK))
    assert result["status"] == status
    assert ctx.deps["failures"] == [status]


def test_track_data_placeholder_retains_loc_without_api_client():
    ctx = SimpleNamespace(deps={"issues": [], "failures": []})
    result = asyncio.run(get_track_data(ctx, ["test-track"], "APOE"))
    assert result["status"] == "unsupported"
    assert result["requested"] == {
        "track_ids": ["test-track"],
        "loc": "APOE",
        "flank": None,
    }


@pytest.mark.parametrize(
    "request_limit,expected_calls,has_error", [(1, 1, True), (2, 2, False)]
)
def test_stream_emits_plan_and_shares_model_budget(
    request_limit, expected_calls, has_error
):
    calls = []

    def model(messages, info):
        calls.append(messages)
        if info.output_tools:
            return ModelResponse(
                parts=[
                    ToolCallPart(info.output_tools[0].name, {"intent": "conversation"})
                ]
            )
        return ModelResponse(parts=[TextPart("Hello.")])

    app = FastAPI()
    app.include_router(router)
    settings = AskSettings(model_requests=request_limit)
    app.dependency_overrides[get_settings] = lambda: settings
    app.dependency_overrides[get_agent] = lambda: build_agent(
        settings, model=FunctionModel(model)
    )
    with TestClient(app) as client:
        response = client.post(
            "/ask",
            json={
                "messages": [
                    {
                        "role": "user",
                        "parts": [{"type": "text", "text": "Hello"}],
                    }
                ]
            },
        )
    assert '"type":"data-niagads-plan"' in response.text
    assert ('"type":"error"' in response.text) == has_error
    assert len(calls) == expected_calls
