"""Fixed API tool operations and bounded results, without database access."""

import asyncio
from types import SimpleNamespace

import httpx
import pytest
from niagads.open_access_api.ask.api_client import retrieve
from niagads.open_access_api.ask.config import AskSettings
from niagads.open_access_api.ask.errors import RetrievalError
from niagads.open_access_api.ask.tools import find_api_operations, search_resources


@pytest.mark.parametrize(
    "operation,parameters,path,kind",
    [
        ("gene", {"gene": "APOE"}, "/record/gene/APOE", "genes"),
        ("variant", {"variant": "RS7412"}, "/record/variant/rs7412", "variants"),
        (
            "variant",
            {"variant": "1:44908822:C:T"},
            "/record/variant/1:44908822:C:T",
            "variants",
        ),
        ("track", {"track": "track-1"}, "/record/track/track-1", "tracks"),
        (
            "variant_associations",
            {"variant": "rs7412", "page": 2, "flank": 10000},
            "/record/variant/rs7412/associations",
            "associations",
        ),
    ],
)
def test_api_tool_uses_registered_record_operation(operation, parameters, path, kind):
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
    assert result.kind == kind


def test_tool_does_not_accept_arbitrary_urls_or_operations():
    async def run():
        async with httpx.AsyncClient(base_url="http://api") as client:
            with pytest.raises(ValueError, match="registered"):
                await retrieve(client, "https://untrusted.example", {})

    asyncio.run(run())


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
            with pytest.raises(RetrievalError, match="not available"):
                await retrieve(client, "region_associations", {"region": "1:10-20"})

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
                with pytest.raises(RetrievalError):
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
            with pytest.raises(RetrievalError, match="invalid response"):
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
                client, "variant_associations", {"variant": "rs7412", "page": 2}
            )
            assert result.page == 2
            assert result.has_more
            assert len(result.rows) == 50
            assert result.warnings
            assert result.sources == ["track-1"]

    asyncio.run(run())


def test_variant_semantic_search_is_unsupported_without_making_an_api_request():
    ctx = SimpleNamespace(deps={})
    result = asyncio.run(search_resources(ctx, query="Alzheimer", entity="variants"))
    assert result["status"] == "unsupported"
    assert ctx.deps["failures"] == ["unsupported"]


@pytest.mark.parametrize("entity", ["tracks", "genes"])
def test_semantic_search_calls_existing_query_api(entity):
    def handler(request):
        assert request.url.path == f"/query/{entity}"
        assert request.url.params["query"] == "Alzheimer"
        assert request.url.params["limit"] == "10"
        return httpx.Response(
            200,
            json={
                "data": [
                    {
                        "matched_record_id": "test-match",
                        "matched_record_details": {"name": "Test semantic candidate"},
                    }
                ]
            },
        )

    async def run():
        async with httpx.AsyncClient(
            transport=httpx.MockTransport(handler), base_url="http://api"
        ) as client:
            return await retrieve(
                client, f"search_{entity}", {"query": "Alzheimer", "limit": 10}
            )

    result = asyncio.run(run())
    assert result.kind == entity
    assert result.rows[0]["id"] == "test-match"
    assert result.warnings


def test_api_help_preserves_planned_operation_status():
    ctx = SimpleNamespace(
        deps={
            "spec": {
                "paths": {
                    "/query/variants": {
                        "get": {"summary": "Query variants", "x-status": "planned"}
                    }
                }
            }
        }
    )
    result = asyncio.run(find_api_operations(ctx, query="variants"))
    assert result["operations"][0]["x-status"] == "planned"
