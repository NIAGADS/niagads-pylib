"""Fixed API tool operations and bounded results, without database access."""

import asyncio

import httpx
import pytest
from niagads.open_access_api.ask.api_client import retrieve
from niagads.open_access_api.ask.config import AskSettings


def test_api_tool_uses_registered_operation_and_bounds_model_data():
    def handler(request):
        assert request.url.path == "/query/tracks"
        assert request.url.params["limit"] == "10"
        return httpx.Response(
            200,
            json={
                "data": [
                    {
                        "matched_record_id": "track-1",
                        "matched_record_details": {"label": "Test track"},
                    },
                ]
            },
        )

    async def run():
        async with httpx.AsyncClient(
            transport=httpx.MockTransport(handler), base_url="http://api"
        ) as client:
            return await retrieve(
                client, "search_tracks", {"query": "test", "limit": 10}
            )

    result = asyncio.run(run())
    assert result.rows[0]["id"] == "track-1"
    assert result.kind == "tracks"


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
            with pytest.raises(NotImplementedError, match="ORM"):
                await retrieve(client, "region_associations", {"region": "1:10-20"})

    asyncio.run(run())


def test_settings_reject_paid_model_and_excessive_limits():
    with pytest.raises(ValueError, match="free"):
        AskSettings(model="paid/model")
    with pytest.raises(ValueError):
        AskSettings(tool_calls=1000)


def test_gene_identifiers_cannot_change_the_registered_path():
    async def run():
        async with httpx.AsyncClient(
            transport=httpx.MockTransport(
                lambda _: httpx.Response(200, json={"data": []})
            ),
            base_url="http://api",
        ) as client:
            for gene in ("..", "../track", "https://untrusted.example"):
                with pytest.raises(ValueError):
                    await retrieve(client, "gene", {"gene": gene})

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
                await retrieve(client, "search_tracks", {"query": "test", "limit": 10})

    asyncio.run(run())


def test_empty_gene_structure_preserves_empty_result():
    async def run():
        async with httpx.AsyncClient(
            transport=httpx.MockTransport(lambda _: httpx.Response(200, json={"data": {}})),
            base_url="http://api",
        ) as client:
            result = await retrieve(client, "gene_structure", {"gene": "APOE"})
            assert result.rows == []

    asyncio.run(run())
