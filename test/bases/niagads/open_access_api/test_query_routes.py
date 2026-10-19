import asyncio
from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from niagads.api.common.models.context.cache import CacheKey, CacheNamespace
from niagads.api.common.models.context.request import Parameters, RequestDetails
from niagads.api.common.models.context.response import ResponseConfiguration
from niagads.api.common.models.responses.records import RecordResponse
from niagads.api.common.services.query import QueryEndpointService
from niagads.common.search.models.record import SearchMatch
from niagads.database.genomicsdb.schema.dataset.track import Track
from niagads.database.genomicsdb.schema.gene.documents import Gene
from niagads.open_access_api.dependencies import OpenAccessEndpointContext
from niagads.open_access_api.routes.query import (
    query_genes,
    query_resources,
    query_tracks,
    query_variants,
    router,
)


@pytest.fixture
def query_client():
    application = FastAPI()
    application.include_router(router)
    context = SimpleNamespace(
        database_session=AsyncMock(),
        request_data=RequestDetails(
            request_id="query-test", endpoint="/query", parameters={}
        ),
        cache_key=CacheKey(key="/query", namespace=CacheNamespace.GENOMICS),
        cache_manager=SimpleNamespace(
            get=AsyncMock(return_value=None), set=AsyncMock()
        ),
    )
    application.dependency_overrides[OpenAccessEndpointContext] = lambda: context
    with TestClient(application) as client:
        yield client, context


@pytest.mark.parametrize(
    "path,expected_ids",
    [
        ("/query", ["track-a", "gene-a"]),
        ("/query/tracks", ["track-a"]),
        ("/query/genes", ["gene-a"]),
    ],
)
def test_query_results(query_client, monkeypatch, path, expected_ids):
    client, context = query_client
    for model, identifier, entity in (
        (Track, "track-a", "TRACK"),
        (Gene, "gene-a", "GENE"),
    ):
        match = SearchMatch(
            matched_record_id=identifier,
            matched_record_details={"label": identifier},
            matched_record_type=entity,
            matched_text="Alzheimer disease",
            match_type="SEMANTIC",
            rank=6,
            score=0.9,
        )
        monkeypatch.setattr(
            model, "semantic_search_by_embedding", AsyncMock(return_value=[match])
        )

    response = client.get(path, params={"query": "Alzheimer disease", "limit": 5})

    assert response.status_code == 200, response.text
    payload = response.json()
    assert [record["id"] for record in payload["data"]] == expected_ids
    assert payload["pagination"]["total_records"] == len(expected_ids)
    for model, identifier in ((Track, "track-a"), (Gene, "gene-a")):
        if identifier in expected_ids:
            model.semantic_search_by_embedding.assert_awaited_once_with(
                context.database_session, "Alzheimer disease", [], limit=5
            )
        else:
            model.semantic_search_by_embedding.assert_not_awaited()


def test_query_variants_not_implemented(query_client):
    client, _ = query_client
    with pytest.raises(
        NotImplementedError, match="Variant semantic search is not yet implemented"
    ):
        client.get("/query/variants", params={"query": "Alzheimer disease"})


@pytest.mark.parametrize(
    "endpoint", [query_resources, query_tracks, query_genes, query_variants]
)
@pytest.mark.parametrize(
    "cached_data",
    [
        [],
        [
            {
                "matched_record_id": "cached-record",
                "matched_record_details": {"label": "Cached record"},
                "matched_record_type": "GENE",
                "matched_text": "Alzheimer disease",
                "match_type": "SEMANTIC",
                "rank": 6,
            }
        ],
    ],
)
def test_query_cache_hit(endpoint, cached_data, monkeypatch):
    context = SimpleNamespace(
        database_session=AsyncMock(),
        request_data=RequestDetails(
            request_id="cache-test", endpoint="/query", parameters={}
        ),
        cache_key=CacheKey(key="/query", namespace=CacheNamespace.GENOMICS),
        cache_manager=SimpleNamespace(
            get=AsyncMock(
                return_value={
                    "data": cached_data,
                    "pagination": {
                        "page": 1,
                        "total_pages": 1,
                        "paged_records": len(cached_data),
                        "total_records": len(cached_data),
                    },
                }
            ),
            set=AsyncMock(),
        ),
    )
    service = QueryEndpointService(
        context=context,
        parameters=Parameters(query="Alzheimer disease", limit=10, page=1),
        response_config=ResponseConfiguration(
            response_model=RecordResponse, record_model=SearchMatch
        ),
    )
    fetch_matches = AsyncMock(side_effect=AssertionError("Cache hit queried ORM"))
    monkeypatch.setattr(service, "fetch_matches", fetch_matches)

    response = asyncio.run(endpoint(service=service))

    assert [record.matched_record_id for record in response.data] == (
        ["cached-record"] if cached_data else []
    )
    assert response.pagination.total_records == len(cached_data)
    context.cache_manager.get.assert_awaited_once_with(
        context.cache_key.encrypt(), namespace=context.cache_key.namespace
    )
    fetch_matches.assert_not_awaited()
