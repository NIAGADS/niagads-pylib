"""Native-loop protocol regressions with recorded evidence, not live LLM validation."""

import asyncio
import json
from copy import deepcopy
from pathlib import Path

import httpx
import pytest
from fastapi import FastAPI
from niagads.api.common.models.entities.gene.records import GeneBrief
from niagads.open_access_api.ask import tools, transport
from niagads.open_access_api.ask.agent import build_agent
from niagads.open_access_api.ask.config import AskSettings
from niagads.open_access_api.ask.contracts import ResultSet
from niagads.open_access_api.ask.planning import QueryPlan
from niagads.open_access_api.ask.results import ResultStore
from pydantic import ValidationError
from pydantic_ai.exceptions import UsageLimitExceeded
from pydantic_ai.messages import (
    ModelResponse,
    TextPart,
    ToolCallPart,
    ToolReturnPart,
    UserPromptPart,
)
from pydantic_ai.models.function import DeltaToolCall, FunctionModel
from pydantic_ai.usage import UsageLimits


@pytest.fixture
def recorded_gene():
    path = Path(__file__).parents[1] / "data" / "gene_record_mapping_response.json"
    return json.loads(path.read_text())["data"]["APOE"][0]


@pytest.fixture
def deps():
    return {
        "client": object(),
        "store": ResultStore(),
        "warnings": [],
        "issues": [],
        "failures": [],
        "spec": {},
        # An initial interpretation must not predict the structure dependency.
        "query_plan": QueryPlan(
            intent="retrieve_data", goal="Retrieve requested evidence"
        ),
    }


def call(name, arguments):
    return ModelResponse(parts=[ToolCallPart(name, arguments)])


def returned(messages):
    """Read the latest native return, including the existing compact snapshot."""
    for message in reversed(messages):
        for part in reversed(message.parts):
            if isinstance(part, ToolReturnPart):
                return part.content
            if isinstance(part, UserPromptPart) and isinstance(part.content, str):
                try:
                    snapshot = json.loads(part.content)
                except ValueError:
                    continue
                if (
                    isinstance(snapshot, dict)
                    and snapshot.get("kind") == "ask_working_context"
                ):
                    exchange = snapshot["exchanges"][-1]
                    if "result_id" in exchange:
                        return {
                            **snapshot["results"][exchange["result_id"]],
                            **exchange.get("details", {}),
                        }
                    return exchange["output"]
    raise AssertionError("Expected authoritative tool evidence")


def test_interpretation_is_flat_and_bounded():
    plan = QueryPlan(
        intent="discover_resources",
        goal="Find matching resources",
        concepts=[{"category": "source", "text": "ENCODE"}],
        constraints=["brain OR blood; preserve the requested source constraint"],
    )
    assert "ConceptGroup" not in json.dumps(QueryPlan.model_json_schema())
    assert plan.constraints
    for extra in (
        {"goal": "x" * 321},
        {"concepts": [{"category": "source", "text": "source"}] * 7},
        {"constraints": ["constraint"] * 7},
        {"clarifications": [{"field": "scope", "question": "Which scope?"}] * 3},
        {"selection": {"operator": "and", "operands": []}},
        {"steps": ["Invent a complete workflow"]},
    ):
        with pytest.raises(ValidationError):
            QueryPlan.model_validate({**plan.model_dump(), **extra})
    model = FunctionModel(
        lambda messages, info: ModelResponse(parts=[TextPart("protocol")])
    )
    assert build_agent(AskSettings(), model=model).model_settings["max_tokens"] == 2000


@pytest.mark.parametrize("outcome", ["present", "clarify", "unsupported"])
def test_native_loop_uses_new_evidence_to_select_dependent_actions(
    monkeypatch, recorded_gene, deps, outcome
):
    operations = []
    responses = []
    structure = recorded_gene["gene_structure"]
    original = deepcopy(structure)
    # Select a real transcript beyond the preview to exercise evidence on demand.
    selected = structure["transcripts"][-1]

    async def retrieve(client, operation, parameters):
        operations.append((operation, parameters))
        if operation == "gene":
            rows = [GeneBrief.model_validate(recorded_gene).model_dump(mode="json")]
            return ResultSet(
                entity="gene", annotation="report", rows=rows, parameters=parameters
            )
        if operation == "region_associations":
            assert parameters == {"region": selected["location"]}
            # Empty API data is evidence too; do not invent association records.
            return ResultSet(
                entity="region",
                annotation="associations",
                rows=[],
                parameters=parameters,
            )
        assert operation == "gene_structure"
        assert parameters == {"gene": recorded_gene["id"]}
        return ResultSet(
            entity="gene",
            annotation="structure",
            rows=[structure],
            parameters=parameters,
        )

    def protocol(messages, info):
        step = len(responses)
        if step == 0:
            response = call("get_gene", {"gene": "APOE"})
        elif step == 1:
            evidence = returned(messages)
            assert evidence["preview"][0]["id"] == recorded_gene["id"]
            assert "gene_structure" not in evidence["preview"][0]
            response = call(
                "get_gene_structure", {"gene": evidence["preview"][0]["id"]}
            )
        elif step == 2:
            evidence = returned(messages)
            assert evidence["transcript_count"] == len(structure["transcripts"])
            assert evidence["transcripts"]
            assert all("exons" not in item for item in evidence["transcripts"])
            if outcome == "clarify":
                assert len(structure["transcripts"]) > 1
                response = call(
                    "clarify_request",
                    {
                        "clarification": {
                            "field": "transcript",
                            "question": "Which transcript should I use?",
                        }
                    },
                )
            elif outcome == "unsupported":
                # Future track-data retrieval must remain honest and make no HTTP call.
                response = call(
                    "get_track_data",
                    {
                        "track_ids": [],
                        "loc": evidence["preview"][0].get(
                            "location", recorded_gene["id"]
                        ),
                    },
                )
            else:
                # A known exact transcript is returned even beyond the initial preview.
                response = call(
                    "get_gene_structure",
                    {
                        "gene": recorded_gene["id"],
                        "transcript": selected["id"],
                        "evidence_fields": ["transcripts"],
                    },
                )
        elif step == 3 and outcome == "present":
            evidence = returned(messages)
            assert evidence["transcripts"] == [
                {
                    key: selected[key]
                    for key in ("id", "name", "location")
                    if key in selected
                }
            ]
            assert evidence["requested_transcript"] == selected["id"]
            assert "exons" not in evidence["transcripts"][0]
            response = call(
                "get_region_associations",
                {"region": evidence["transcripts"][0]["location"]},
            )
        elif step == 4 and outcome == "present":
            evidence = returned(messages)
            assert evidence["parameters"] == {"region": selected["location"]}
            assert evidence["count"] == 0
            response = call(
                "present_results",
                {"presentation": {"result_id": evidence["result_id"], "view": "table"}},
            )
        else:
            evidence = returned(messages)
            assert (
                evidence["status"]
                == {
                    "present": "recorded",
                    "clarify": "clarification",
                    "unsupported": "unsupported",
                }[outcome]
            )
            text = (
                "Which transcript should I use?"
                if outcome == "clarify"
                else "Retrieved evidence is available; remaining capability limits are reported."
            )
            response = ModelResponse(parts=[TextPart(text)])
        responses.append(response)
        return response

    monkeypatch.setattr(tools, "retrieve", retrieve)
    agent = build_agent(AskSettings(), model=FunctionModel(protocol))
    result = asyncio.run(
        agent.run(
            "Protocol: inspect requested evidence",
            deps=deps,
            usage_limits=UsageLimits(request_limit=8, tool_calls_limit=12),
        )
    )
    assert result.output
    assert len(responses) == (6 if outcome == "present" else 4)
    assert len(operations) == (4 if outcome == "present" else 2)
    assert structure == original
    stored = list(deps["store"].results.values())
    assert stored[1].rows == [original]
    if outcome == "present":
        assert deps["store"].presentations[0].result_id == stored[-1].id
        assert deps["failures"] == []
    else:
        assert deps["failures"] == [
            {"clarify": "clarification", "unsupported": "unsupported"}[outcome]
        ]
        assert deps["store"].presentations == []
        assert len(stored) == 2


@pytest.mark.parametrize("budget", ["requests", "tools"])
def test_native_loop_stops_at_existing_usage_limits(deps, budget):
    calls = []

    def protocol(messages, info):
        calls.append(messages)
        return call("find_api_operations", {"query": "region"})

    agent = build_agent(AskSettings(), model=FunctionModel(protocol))
    limits = (
        UsageLimits(request_limit=2, tool_calls_limit=12)
        if budget == "requests"
        else UsageLimits(request_limit=8, tool_calls_limit=1)
    )
    with pytest.raises(UsageLimitExceeded):
        asyncio.run(
            agent.run(
                "Protocol: keep requesting operations", deps=deps, usage_limits=limits
            )
        )
    assert len(calls) == 2
    assert deps["store"].results == {}


def test_active_deadline_preserves_evidence_and_closes_native_stream(
    monkeypatch, recorded_gene
):
    retrieved = ResultSet(
        entity="gene",
        annotation="report",
        rows=[recorded_gene],
        parameters={"gene": "APOE"},
    )

    async def retrieve(*args):
        return retrieved

    calls = []

    async def protocol(messages, info):
        calls.append(messages)
        if len(calls) == 1:
            yield {
                0: DeltaToolCall(
                    name="get_gene", json_args='{"gene":"APOE"}', tool_call_id="record"
                )
            }
        else:
            # Simulate active provider work, not retry backoff; no real network.
            await asyncio.Future()

    settings = AskSettings(deadline=1, feedback_enable=False)
    agent = build_agent(settings, model=FunctionModel(stream_function=protocol))
    monkeypatch.setattr(tools, "retrieve", retrieve)
    app = FastAPI()
    app.include_router(transport.router)
    app.dependency_overrides[transport.get_agent] = lambda: agent
    app.dependency_overrides[transport.get_settings] = lambda: settings

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
    events = [
        json.loads(line[6:])
        for line in response.text.splitlines()
        if line.startswith("data: {")
    ]
    envelope = next(
        event["data"] for event in events if event["type"] == "data-niagads-result"
    )
    assert envelope["results"] == [retrieved.model_dump(mode="json")]
    assert envelope["status"] == "retrieval_error"
    assert len(calls) == 2
    errors = [event for event in events if event["type"] == "error"]
    assert len(errors) == 1
    assert "TimeoutError" in errors[0]["errorText"]
    assert "id" not in errors[0]  # Optional null fields must not leak into SDK events.
    assert response.text.rstrip().endswith("data: [DONE]")


def test_gene_evidence_can_be_selected_after_interpretation(
    monkeypatch, recorded_gene, deps
):
    retrieved = ResultSet(entity="gene", annotation="report", rows=[recorded_gene])
    seen = []

    async def retrieve(client, operation, parameters):
        assert operation == "gene_full"
        return retrieved

    def protocol(messages, info):
        seen.append(messages)
        if len(seen) == 1:
            return call(
                "get_gene",
                {
                    "gene": "APOE",
                    "content": "full",
                    "evidence_fields": ["functional_annotation"],
                },
            )
        summary = returned(messages)
        assert summary["evidence_fields"] == ["functional_annotation"]
        assert (
            summary["gene_annotations"][0]["functional_annotation"]
            == recorded_gene["functional_annotation"]
        )
        assert "publications" not in summary["gene_annotations"][0]
        return ModelResponse(parts=[TextPart("Requested annotations were retrieved.")])

    monkeypatch.setattr(tools, "retrieve", retrieve)
    agent = build_agent(AskSettings(), model=FunctionModel(protocol))
    asyncio.run(agent.run("Protocol: select annotation evidence", deps=deps))
    assert deps["query_plan"].gene_evidence == []
    assert deps["store"].get(retrieved.id).rows == [recorded_gene]


@pytest.mark.parametrize("mode", ["direct", "planned", "invalid_plan"])
def test_annotation_request_reaches_native_retrieval_without_mandatory_planning(
    monkeypatch, recorded_gene, mode
):
    """Protocol evidence checks the route boundary, not live model interpretation."""
    gene = ResultSet(
        entity="gene",
        annotation="report",
        rows=[recorded_gene],
        sources=[recorded_gene["id"]],
        parameters={"gene": "APOE"},
    )
    associations = ResultSet(
        entity="gene",
        annotation="associations",
        rows=[],  # Empty API evidence must not erase the retrieved gene annotations.
        parameters={"gene": recorded_gene["id"], "page": 1, "flank": 0},
    )
    calls, operations = [], []
    interpretation = {
        "goal": "Retrieve gene annotations and associated dataset/association evidence",
        "intent": "retrieve_data",
        "entity": "gene",
        "gene_evidence": ["functional_annotation", "memberships"],
    }
    # Supplied malformed completion: invalid JSON, not evidence of token truncation.
    malformed = (
        '[[{"name": "final_result", "parameters": {"intent": "discover_resources", '
        '"entity": "track", "selection": {"operator": "and", "operands": '
        '[{"category": "annotation", "text": "annotation"}]}, "location": '
        '{"kind": "gene", "loc": "APOE"}, "clarifications": [], '
        '"exclusions": [], "gene_evidence": []}}]'
    )

    async def retrieve(client, operation, parameters):
        operations.append((operation, parameters))
        if operation == "gene_full":
            assert parameters == {"gene": "APOE"}
            return gene
        assert operation == "gene_associations"
        assert parameters == associations.parameters
        return associations

    async def protocol(messages, info):
        step = len(calls)
        calls.append(messages)
        if step == 0:
            name, arguments = "get_gene", {
                "gene": "APOE",
                "content": "full",
                "evidence_fields": ["functional_annotation", "memberships"],
            }
        elif mode == "invalid_plan":
            yield {
                0: DeltaToolCall(
                    name="record_query_plan",
                    json_args=malformed,
                    tool_call_id=f"invalid-{step}",
                )
            }
            return
        elif mode == "planned" and step == 1:
            evidence = returned(messages)
            assert evidence["gene_annotations"][0]["id"] == recorded_gene["id"]
            name, arguments = "record_query_plan", {"interpretation": interpretation}
        elif step == (2 if mode == "planned" else 1):
            if mode == "planned":
                assert returned(messages)["status"] == "recorded"
            else:
                evidence = returned(messages)
                assert (
                    evidence["gene_annotations"][0]["functional_annotation"]
                    == recorded_gene["functional_annotation"]
                )
            name, arguments = "get_gene_associations", {"gene": recorded_gene["id"]}
        elif step == (3 if mode == "planned" else 2):
            evidence = returned(messages)
            assert evidence["result_id"] == associations.id
            assert evidence["count"] == 0
            name, arguments = "present_results", {
                "presentation": {"result_id": evidence["result_id"], "view": "table"}
            }
        else:
            yield "Gene annotations were retrieved; no association records were returned."
            return
        yield {
            0: DeltaToolCall(
                name=name, json_args=json.dumps(arguments), tool_call_id=f"call-{step}"
            )
        }

    # Streaming-only model: the obsolete mandatory non-streaming planner cannot run.
    settings = AskSettings(feedback_enable=False)
    agent = build_agent(settings, model=FunctionModel(stream_function=protocol))
    app = FastAPI()
    app.include_router(transport.router)
    app.dependency_overrides[transport.get_agent] = lambda: agent
    app.dependency_overrides[transport.get_settings] = lambda: settings
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
                            "parts": [
                                {
                                    "type": "text",
                                    "text": "Show the available annotations for APOE",
                                }
                            ],
                        }
                    ]
                },
            )

    response = asyncio.run(request())
    events = [
        json.loads(line[6:])
        for line in response.text.splitlines()
        if line.startswith("data: {")
    ]
    envelope = next(
        event["data"] for event in events if event["type"] == "data-niagads-result"
    )
    plans = [event for event in events if event["type"] == "data-niagads-plan"]
    errors = [event for event in events if event["type"] == "error"]
    assert envelope["results"][0] == gene.model_dump(mode="json")
    assert response.text.rstrip().endswith("data: [DONE]")
    if mode == "invalid_plan":
        assert len(operations) == 1
        assert len(calls) == 3
        assert not plans
        assert errors and "UnexpectedModelBehavior" in errors[0]["errorText"]
        assert envelope["status"] == "retrieval_error"
        assert len(envelope["results"]) == 1
    else:
        assert [operation for operation, _ in operations] == [
            "gene_full",
            "gene_associations",
        ]
        assert envelope["results"][1] == associations.model_dump(mode="json")
        assert envelope["presentation"][0]["result_id"] == associations.id
        assert not errors
        assert len(calls) == (5 if mode == "planned" else 4)
        assert len(plans) == (1 if mode == "planned" else 0)
        if plans:
            assert plans[0]["data"] == QueryPlan.model_validate(
                interpretation
            ).model_dump(mode="json")
            assert "id" not in plans[0]
            assert "transient" not in plans[0]
