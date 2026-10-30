import asyncio
from unittest.mock import AsyncMock, MagicMock, call

import pytest
from niagads.api.common.parameters.identifiers import region_id
from niagads.api.common.services.base import BaseEndpointService
from niagads.api.common.types import ResponseContent, ResponseFormat
from niagads.open_access_api.routes.records import region as region_routes


@pytest.mark.parametrize("content", ["full", "summary"])
@pytest.mark.parametrize("chromosome", ["1", "chr1"])
def test_get_region_associations(client, content, chromosome):
    response = client.get(
        f"/record/region/{chromosome}:3765506-3765506/associations",
        params={"content": content},
    )

    assert response.status_code == 200, response.text
    records = response.json()["data"]
    assert records
    for record in records:
        assert record["track"]
        assert isinstance(record["traits"], dict)
        if content == "full":
            assert record["variant"]
            assert record["position"] == 3765506
            assert isinstance(record["pvalue"], str)
        else:
            assert record["num_associations"] > 0


@pytest.mark.parametrize("content", ["full", "summary"])
@pytest.mark.parametrize("chromosome", ["1", "chr1"])
def test_get_region_variants(client, content, chromosome):
    response = client.get(
        f"/record/region/{chromosome}:3765506-3765506/variants",
        params={"content": content},
    )

    assert response.status_code == 200, response.text
    records = response.json()["data"]
    assert records
    for record in records:
        assert record["id"]
        assert record["variant_class"]
        if content == "full":
            assert record["position"] == 3765506
        else:
            assert "position" not in record


@pytest.mark.parametrize("annotation", ["associations", "variants"])
@pytest.mark.parametrize(
    "region",
    [
        "invalid",
        "chr1:200-100",
        "chr1:100-end",
        "chr1:1-100000",
        "chr1:1-100001",
    ],
)
def test_get_region_invalid_coordinates(client, annotation, region):
    response = client.get(f"/record/region/{region}/{annotation}")

    assert response.status_code == 422, response.text


@pytest.mark.parametrize("annotation", ["associations", "variants"])
def test_get_region_requires_path_identifier(client, annotation):
    response = client.get(
        f"/record/region/{annotation}",
        params={"region": "chr1:100-200"},
    )

    assert response.status_code == 404, response.text


def test_region_span_below_limit():
    feature = asyncio.run(region_id("chr1:1-99999"))

    assert feature.feature_id == "chr1:1-99999"


@pytest.mark.parametrize("count", [0, 5000, 5001, 50000])
def test_region_variants_count_and_limit(monkeypatch, count):
    service = MagicMock()
    service.get_cached_response = AsyncMock(return_value=None)
    service.fetch_variants = AsyncMock(side_effect=[count, []])
    service.generate_response = AsyncMock()
    monkeypatch.setattr(
        region_routes, "RegionEndpointService", MagicMock(return_value=service)
    )

    asyncio.run(
        region_routes.get_region_variants(
            region=asyncio.run(region_id("chr1:1-99999")),
            context=None,
            format=ResponseFormat.JSON,
            content=ResponseContent.FULL,
            page=1,
        )
    )

    assert service.fetch_variants.await_args_list == [
        call("chr1:1-99999", counts_only=True),
        call("chr1:1-99999", limit=5000),
    ]
    message = service.generate_response.await_args.kwargs["message"]
    if count > 5000:
        assert message == [
            f"{count:,} variants found in region, returning first 5,000. "
            "Please run windowed queries to fetch across the whole region."
        ]
    else:
        assert message is None


def test_cached_region_truncation_message():
    context = MagicMock()
    context.cache_manager.set = AsyncMock()
    response_config = MagicMock(record_model=None)
    service = BaseEndpointService(
        context=context,
        parameters=MagicMock(),
        response_config=response_config,
    )
    message = [
        "50,000 variants found in region, returning first 5,000. "
        "Please run windowed queries to fetch across the whole region."
    ]
    cached_response = {"data": [], "pagination": None, "message": message}

    asyncio.run(service.generate_response(cached_response, from_cache=True))

    assert response_config.response_model.call_args.kwargs["message"] == message
    assert context.cache_manager.set.await_args.args[1]["message"] == message
