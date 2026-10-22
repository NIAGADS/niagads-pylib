"""Tool capability limits preserve successful retrievals and conversation state."""

from unittest.mock import Mock

import httpx
import pytest
from niagads.api.common.types import ResponseContent
from niagads.common.types import Entity
from niagads.open_access_api.ask.contracts import ResultFilter, ResultSet
from niagads.open_access_api.ask.planning import QueryIntent, QueryPlan
from niagads.open_access_api.ask.results import ResultStore
from niagads.open_access_api.ask.tools import (
    filter_results,
    get_feature_location,
    get_gene,
    get_region_associations,
    get_region_variants,
    get_track,
    search_resources,
)
from pydantic_ai import ModelRetry, RunContext
from pydantic_ai.models.test import TestModel
from pydantic_ai.usage import RunUsage


@pytest.mark.anyio
@pytest.mark.parametrize("anyio_backend", ["asyncio"])
async def test_near_gene_variants_and_filter_reuse_retrieved_page(anyio_backend):
    rows = [
        {"id": "6:100:A:T", "is_adsp_variant": True},
        {"id": "6:101:C:T", "is_adsp_variant": False},
        {"id": "6:102:G:T", "is_adsp_variant": None},
        {"id": "6:103:A:C"},
    ]
    handler = Mock(
        side_effect=[
            httpx.Response(200, json={"chr": "chr6", "start": 90, "end": 200}),
            httpx.Response(200, json={"data": rows}),
        ]
    )
    store = ResultStore()
    async with httpx.AsyncClient(
        transport=httpx.MockTransport(handler), base_url="http://api"
    ) as client:
        ctx = RunContext(
            deps={"client": client, "store": store},
            model=TestModel(),
            usage=RunUsage(),
        )
        location = await get_feature_location(ctx, "TREM2", flank=10000)
        result = await get_region_variants(ctx, location["region"])
        filtered = await filter_results(
            ctx,
            result["result_id"],
            [ResultFilter(field="is_adsp_variant", value=True)],
        )

    requests = [call.args[0] for call in handler.call_args_list]
    assert len(requests) == 2
    assert requests[0].url.path == "/service/feature"
    assert requests[0].url.params["id"] == "TREM2"
    assert requests[0].url.params["flank"] == "10000"
    assert requests[1].url.path == "/record/region/6:90-200/variants"
    assert requests[1].url.params["content"] == "full"
    assert store.get(result["result_id"]).rows == rows
    assert filtered["matching_count"] == 1
    assert store.presentations[0].filters[0].value is True


@pytest.mark.anyio
@pytest.mark.parametrize("anyio_backend", ["asyncio"])
async def test_region_variant_cap_warning_survives_filtering(anyio_backend):
    warning = (
        "50,000 variants found in region, returning first 5,000. "
        "Please run windowed queries to fetch across the whole region."
    )
    handler = Mock(
        return_value=httpx.Response(
            200,
            json={
                "data": [{"id": "1:100:A:T", "is_adsp_variant": False}],
                "pagination": {"total_pages": 1},
                "message": [warning],
            },
        )
    )
    store = ResultStore()
    async with httpx.AsyncClient(
        transport=httpx.MockTransport(handler), base_url="http://api"
    ) as client:
        ctx = RunContext(
            deps={"client": client, "store": store},
            model=TestModel(),
            usage=RunUsage(),
        )
        summary = await get_region_variants(ctx, "1:100-200")
        filtered = await filter_results(
            ctx,
            summary["result_id"],
            [ResultFilter(field="is_adsp_variant", value=True)],
        )

    assert summary["warnings"] == [warning]
    assert summary["has_more"] is False
    assert store.get(summary["result_id"]).warnings == [warning]
    assert filtered["matching_count"] == 0
    assert handler.call_count == 1


@pytest.mark.anyio
@pytest.mark.parametrize("anyio_backend", ["asyncio"])
async def test_result_filter_rejects_unretrieved_field(anyio_backend):
    store = ResultStore()
    result = store.add(
        ResultSet(entity=Entity.VARIANT, annotation=None, rows=[{"id": "v1"}])
    )
    ctx = RunContext(deps={"store": store}, model=TestModel(), usage=RunUsage())
    with pytest.raises(ModelRetry, match="Unknown filter field"):
        await filter_results(
            ctx, result.id, [ResultFilter(field="invented", value=True)]
        )
    assert not store.presentations


@pytest.mark.anyio
@pytest.mark.parametrize("anyio_backend", ["asyncio"])
@pytest.mark.parametrize("region", ["1:100-200", "chr1:100-200"])
@pytest.mark.parametrize("content", [ResponseContent.FULL, ResponseContent.SUMMARY])
async def test_region_associations_use_validated_path(anyio_backend, region, content):
    handler = Mock(return_value=httpx.Response(200, json={"data": []}))
    async with httpx.AsyncClient(
        transport=httpx.MockTransport(handler), base_url="http://api"
    ) as client:
        ctx = RunContext(
            deps={"client": client, "store": ResultStore()},
            model=TestModel(),
            usage=RunUsage(),
        )

        summary = await get_region_associations(ctx, region, content=content)

    request = handler.call_args.args[0]
    assert request.url.path == "/record/region/1:100-200/associations"
    assert "region" not in request.url.params
    assert request.url.params["content"] == content.value
    assert summary["count"] == 0


@pytest.mark.anyio
@pytest.mark.parametrize("anyio_backend", ["asyncio"])
@pytest.mark.parametrize("has_results", [False, True])
async def test_collection_search_is_a_nonfatal_limitation(anyio_backend, has_results):
    store = ResultStore()
    if has_results:
        result = ResultSet(
            entity=Entity.TRACK,
            annotation=None,
            rows=[{"id": "track-1"}],
        )
        store.add(result)
    deps = {"store": store, "warnings": [], "failures": [], "issues": []}
    ctx = RunContext(deps=deps, model=TestModel(), usage=RunUsage())

    summary = await search_resources(ctx, "Alzheimer disease", Entity.COLLECTION)

    assert summary["status"] == "unsupported"
    assert "Collection search is not yet available" in summary["detail"]
    assert deps["failures"] == []
    assert deps["issues"] == []
    assert deps["warnings"] == [summary["detail"]]
    if has_results:
        assert store.get(result.id).rows == [{"id": "track-1"}]
    else:
        assert not store.results


@pytest.mark.anyio
@pytest.mark.parametrize("anyio_backend", ["asyncio"])
@pytest.mark.parametrize(
    "status,rows",
    [(200, [{"id": "ENSG00000130203"}]), (200, []), (404, [])],
)
async def test_gene_lookup_searches_only_after_no_match(anyio_backend, status, rows):
    handler = Mock(
        side_effect=[
            httpx.Response(status, json={"data": rows}),
            httpx.Response(200, json={"data": [{"id": "candidate-1"}]}),
        ]
    )
    async with httpx.AsyncClient(
        transport=httpx.MockTransport(handler), base_url="http://api"
    ) as client:
        deps = {"client": client, "store": ResultStore()}
        ctx = RunContext(deps=deps, model=TestModel(), usage=RunUsage())

        summary = await get_gene(ctx, "APOE")

    requests = [call.args[0] for call in handler.call_args_list]
    assert requests[0].url.path == "/record/gene/APOE"
    result = deps["store"].get(summary["result_id"])
    if rows:
        assert len(requests) == 1
        assert result.rows == [{"id": "ENSG00000130203"}]
    else:
        assert len(requests) == 2
        assert requests[1].url.path == "/query/genes"
        assert requests[1].url.params["text"] == "APOE"
        assert result.rows == [{"id": "candidate-1"}]


@pytest.mark.anyio
@pytest.mark.parametrize("anyio_backend", ["asyncio"])
async def test_gene_lookup_failure_does_not_trigger_semantic_search(anyio_backend):
    handler = Mock(return_value=httpx.Response(503, json={"detail": "unavailable"}))
    async with httpx.AsyncClient(
        transport=httpx.MockTransport(handler), base_url="http://api"
    ) as client:
        ctx = RunContext(
            deps={"client": client, "store": ResultStore()},
            model=TestModel(),
            usage=RunUsage(),
        )

        with pytest.raises(RuntimeError, match="HTTP 503"):
            await get_gene(ctx, "APOE")

    assert handler.call_count == 1


@pytest.mark.anyio
@pytest.mark.parametrize("anyio_backend", ["asyncio"])
@pytest.mark.parametrize("content", [ResponseContent.FULL, ResponseContent.SUMMARY])
async def test_gene_lookup_exposes_curated_evidence(
    anyio_backend, content, example_gene_record_mapping_response
):
    row = dict(example_gene_record_mapping_response["data"]["APOE"][0])
    curated_lists = row["memberships"]["curated_lists"]
    if content == ResponseContent.SUMMARY:
        row.pop("memberships")
    handler = Mock(return_value=httpx.Response(200, json={"data": [row]}))
    async with httpx.AsyncClient(
        transport=httpx.MockTransport(handler), base_url="http://api"
    ) as client:
        store = ResultStore()
        ctx = RunContext(
            deps={"client": client, "store": store},
            model=TestModel(),
            usage=RunUsage(),
        )

        summary = await get_gene(ctx, "APOE", content=content)

    request = handler.call_args.args[0]
    assert request.url.path == "/record/gene/APOE"
    assert request.url.params["content"] == content.value
    result = store.get(summary["result_id"])
    assert result.content == content
    assert result.rows == [row]
    evidence = summary["gene_evidence"][0]
    assert evidence["id"] == row["id"]
    if "associated_with_known_ad_locus" in row:
        assert (
            evidence["associated_with_known_ad_locus"]
            == row["associated_with_known_ad_locus"]
        )
    if content == ResponseContent.FULL:
        assert curated_lists
        assert evidence["curated_lists"] == curated_lists
    else:
        assert "curated_lists" not in evidence


@pytest.mark.anyio
@pytest.mark.parametrize("anyio_backend", ["asyncio"])
@pytest.mark.parametrize(
    "needs_clarification,has_exclusions",
    [(True, False), (False, True), (True, True)],
)
async def test_plan_limitations_do_not_block_independent_retrieval(
    anyio_backend, needs_clarification, has_exclusions
):
    plan = QueryPlan(
        goal="Protocol interpretation",
        intent=QueryIntent.DISCOVER_RESOURCES,
        clarifications=(
            [{"field": "location", "question": "Which region?"}]
            if needs_clarification
            else []
        ),
        exclusions=["ENCODE"] if has_exclusions else [],
    )
    async with httpx.AsyncClient(
        transport=httpx.MockTransport(
            lambda _: httpx.Response(200, json={"data": [{"id": "track-1"}]})
        ),
        base_url="http://api",
    ) as client:
        deps = {
            "client": client,
            "store": ResultStore(),
            "query_plan": plan,
            "warnings": [],
            "failures": [],
            "issues": [],
        }
        ctx = RunContext(deps=deps, model=TestModel(), usage=RunUsage())

        summary = await get_track(ctx, "track-1")

    assert summary["count"] == 1
    assert deps["store"].get(summary["result_id"]).rows == [{"id": "track-1"}]
    assert deps["failures"] == []
    assert deps["issues"] == []
