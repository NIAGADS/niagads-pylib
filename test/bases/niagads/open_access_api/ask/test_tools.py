"""Fixed API tool operations and bounded results, without database access."""

import asyncio
from types import SimpleNamespace

import httpx
import pytest
from niagads.api.common.models.context.response import ResponseConfiguration
from niagads.api.common.models.records.types import DynamicRecord
from niagads.api.common.models.responses.records import RecordResponse
from niagads.common.types import Entity
from niagads.open_access_api.ask.api_client import retrieve
from niagads.open_access_api.ask.config import AskSettings
from niagads.open_access_api.ask.operations import OPERATIONS, AskOperation
from niagads.open_access_api.ask.results import ResultStore
from niagads.open_access_api.ask.tools import (
    find_api_operations,
    search_resources,
)


@pytest.mark.parametrize(
    "operation,parameters,path,entity,annotation",
    [
        ("gene", {"gene": "APOE"}, "/record/gene/APOE", "gene", "report"),
        (
            "variant",
            {"variant": "RS7412"},
            "/record/variant/rs7412",
            "variant",
            "report",
        ),
        (
            "variant",
            {"variant": "1:44908822:C:T"},
            "/record/variant/1:44908822:C:T",
            "variant",
            "report",
        ),
        (
            "track",
            {"track": "track-1"},
            "/record/track/track-1",
            "track",
            "report",
        ),
        (
            "variant_associations",
            {"variant": "rs7412", "page": 2, "flank": 10000},
            "/record/variant/rs7412/associations",
            "variant",
            "associations",
        ),
    ],
)
def test_api_tool_uses_registered_record_operation(
    operation, parameters, path, entity, annotation
):
    def handler(request):
        assert request.url.path == path
        if operation == "variant_associations":
            assert request.url.params["page"] == "2"
            assert request.url.params["flank"] == "10000"
        return httpx.Response(200, json={"data": [{"id": "record-1"}]})

    async def run():
        async with httpx.AsyncClient(
            transport=httpx.MockTransport(handler), base_url="http://api"
        ) as client:
            return await retrieve(client, operation, parameters)

    result = asyncio.run(run())
    assert result.rows[0]["id"] == "record-1"
    assert result.entity == entity
    assert result.annotation == annotation


def test_tool_does_not_accept_arbitrary_urls_or_operations():
    async def run():
        async with httpx.AsyncClient(base_url="http://api") as client:
            with pytest.raises(ValueError, match="registered"):
                await retrieve(client, "https://untrusted.example", {})

    asyncio.run(run())


def test_registered_entity_uses_its_own_identifier_parameter(monkeypatch):
    monkeypatch.setitem(
        OPERATIONS,
        "collection_report",
        AskOperation(
            endpoint="/record/collection/{collection}",
            entity=Entity.COLLECTION,
            annotation="report",
            response_config=ResponseConfiguration(
                response_model=RecordResponse, record_model=DynamicRecord
            ),
        ),
    )

    def handler(request):
        assert request.url.path == "/record/collection/collection-1"
        assert "collection" not in request.url.params
        return httpx.Response(200, json={"data": [{"id": "collection-1"}]})

    async def run():
        async with httpx.AsyncClient(
            transport=httpx.MockTransport(handler), base_url="http://api"
        ) as client:
            return await retrieve(
                client, "collection_report", {"collection": "collection-1"}
            )

    result = asyncio.run(run())
    assert result.entity == Entity.COLLECTION
    assert result.annotation == "report"
    assert result.rows == [{"id": "collection-1"}]


def test_missing_region_retrieval_is_not_reported_as_empty_success():
    async def run():
        async with httpx.AsyncClient(
            transport=httpx.MockTransport(
                lambda _: httpx.Response(
                    501, json={"detail": "ORM integration pending"}
                )
            ),
            base_url="http://api",
        ) as client:
            with pytest.raises(NotImplementedError, match="ORM"):
                await retrieve(
                    client, "region_associations", {"region": "1:10-20"}
                )

    asyncio.run(run())


def test_settings_reject_excessive_limits():
    with pytest.raises(ValueError):
        AskSettings(tool_calls=1000)


@pytest.mark.parametrize("operation", ["gene", "variant", "track"])
def test_record_identifiers_cannot_change_the_registered_path(operation):
    async def run():
        async with httpx.AsyncClient(
            transport=httpx.MockTransport(
                lambda _: httpx.Response(200, json={"data": []})
            ),
            base_url="http://api",
        ) as client:
            for identifier in ("..", "../track", "https://untrusted.example"):
                with pytest.raises(ValueError):
                    await retrieve(client, operation, {operation: identifier})

    asyncio.run(run())


def test_invalid_api_envelope_is_not_reported_as_no_matches():
    async def run():
        async with httpx.AsyncClient(
            transport=httpx.MockTransport(
                lambda _: httpx.Response(200, json={"message": "missing data"})
            ),
            base_url="http://api",
        ) as client:
            with pytest.raises(ValueError, match="envelope"):
                await retrieve(client, "track", {"track": "track-1"})

    asyncio.run(run())


def test_empty_gene_structure_preserves_empty_result():
    async def run():
        async with httpx.AsyncClient(
            transport=httpx.MockTransport(
                lambda _: httpx.Response(200, json={"data": []})
            ),
            base_url="http://api",
        ) as client:
            result = await retrieve(client, "gene_structure", {"gene": "APOE"})
            assert result.rows == []

    asyncio.run(run())


def test_record_tool_reports_truncated_page_and_preserves_pagination():
    async def run():
        async with httpx.AsyncClient(
            transport=httpx.MockTransport(
                lambda _: httpx.Response(
                    200,
                    json={
                        "data": [{"track": "track-1"} for _ in range(51)],
                        "pagination": {"page": 2, "total_pages": 3},
                    },
                )
            ),
            base_url="http://api",
        ) as client:
            result = await retrieve(
                client,
                "variant_associations",
                {"variant": "rs7412", "page": 2},
            )
            assert result.page == 2
            assert result.has_more
            assert len(result.rows) == 50
            assert result.warnings
            assert result.sources == ["track-1"]

    asyncio.run(run())


def test_variant_semantic_search_is_unsupported_without_making_an_api_request():
    ctx = SimpleNamespace(deps={})
    result = asyncio.run(
        search_resources(ctx, query="Alzheimer", entity=Entity.VARIANT)
    )
    assert result["status"] == "unsupported"
    assert ctx.deps["failures"] == ["unsupported"]


@pytest.mark.parametrize(
    "entity,path",
    [(Entity.TRACK, "/query/tracks"), (Entity.GENE, "/query/genes")],
)
def test_semantic_search_calls_existing_query_api(entity, path):
    def handler(request):
        assert request.url.path == path
        assert request.url.params["query"] == "Alzheimer"
        assert request.url.params["limit"] == "10"
        return httpx.Response(
            200,
            json={
                "data": [
                    {
                        "matched_record_id": "test-match",
                        "matched_record_details": {
                            "name": "Test semantic candidate"
                        },
                    }
                ]
            },
        )

    async def run():
        async with httpx.AsyncClient(
            transport=httpx.MockTransport(handler), base_url="http://api"
        ) as client:
            ctx = SimpleNamespace(
                deps={"client": client, "store": ResultStore()}
            )
            summary = await search_resources(
                ctx, query="Alzheimer", entity=entity
            )
            return ctx.deps["store"].get(summary["result_id"])

    result = asyncio.run(run())
    assert result.entity == entity
    assert result.annotation is None
    assert result.rows[0]["id"] == "test-match"
    assert result.warnings


def test_api_help_preserves_planned_operation_status():
    ctx = SimpleNamespace(
        deps={
            "spec": {
                "paths": {
                    "/query/variants": {
                        "get": {
                            "summary": "Query variants",
                            "x-status": "planned",
                        }
                    }
                }
            }
        }
    )
    result = asyncio.run(find_api_operations(ctx, query="variants"))
    assert result["operations"][0]["x-status"] == "planned"


@pytest.mark.parametrize(
    "tool,identifier,path",
    [
        (
            get_gene_associations,
            {"gene": "APOE"},
            "/record/gene/APOE/associations",
        ),
        (
            get_variant_associations,
            {"variant": "rs7412"},
            "/record/variant/rs7412/associations",
        ),
    ],
)
def test_association_tools_request_existing_api_summary(
    tool, identifier, path
):
    def handler(request):
        assert request.url.path == path
        assert request.url.params["content"] == "summary"
        assert request.url.params["page"] == "2"
        assert request.url.params["flank"] == "10000"
        return httpx.Response(
            200,
            json={
                "data": [
                    {
                        "track": "track-a",
                        "traits": {},
                        "num_associations": 1200,
                    }
                ]
            },
        )

    async def run():
        async with httpx.AsyncClient(
            transport=httpx.MockTransport(handler), base_url="http://api"
        ) as client:
            ctx = SimpleNamespace(
                deps={"client": client, "store": ResultStore()}
            )
            summary = await tool(
                ctx,
                **identifier,
                content=ResponseContent.SUMMARY,
                page=2,
                flank=10000,
            )
            return ctx.deps["store"].get(summary["result_id"])

    result = asyncio.run(run())
    assert result.content == ResponseContent.SUMMARY
    assert result.rows[0]["num_associations"] == 1200
    assert result.sources == ["track-a"]
