"""OpenRouter query embedding contracts without provider or database access."""

import asyncio
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock

import pytest
from niagads.api.common.config import QueryEmbeddingSettings
from niagads.api.common.models.context.request import Parameters
from niagads.api.common.models.context.response import ResponseConfiguration
from niagads.api.common.models.responses.records import RecordResponse
from niagads.api.common.services import embeddings, query
from niagads.api.common.services.embeddings import OpenRouterQueryEmbedding
from niagads.common.search.models.record import SearchMatch


def test_embedding_model_is_configurable_and_currently_restricted():
    model = "liquid/lfm-2.5-embedding-350m:free"
    settings = QueryEmbeddingSettings(
        OPENROUTER_API_KEY="synthetic-test-key", OPENROUTER_EMBEDDING_MODEL=model
    )
    assert settings.OPENROUTER_EMBEDDING_MODEL == model
    with pytest.raises(ValueError):
        QueryEmbeddingSettings(
            OPENROUTER_API_KEY="synthetic-test-key",
            OPENROUTER_EMBEDDING_MODEL="another/model",
        )


@pytest.mark.parametrize(
    "vector",
    [[], [0.0, 0.0], [float("nan"), 1.0], [float("inf")], ["not-a-vector"]],
)
def test_invalid_vectors_fail_before_retrieval(vector):
    with pytest.raises(RuntimeError, match="invalid query embedding"):
        OpenRouterQueryEmbedding.normalize_embedding(
            {"model": "test-model", "data": [{"index": 0, "embedding": vector}]},
            "test-model",
        )


def test_embedding_model_substitution_is_rejected():
    with pytest.raises(RuntimeError, match="different model"):
        OpenRouterQueryEmbedding.normalize_embedding(
            {"model": "different-model", "data": [{"index": 0, "embedding": [1.0]}]},
            "test-model",
        )


def test_openrouter_request_uses_configured_id_raw_query_and_server_key(monkeypatch):
    result = MagicMock()
    result.json = AsyncMock(
        return_value={
            "model": "liquid/lfm-2.5-embedding-350m:free",
            "data": [{"index": 0, "embedding": [3.0, 4.0]}],
        }
    )
    session = MagicMock()
    session.post.return_value.__aenter__.return_value = result
    manager = AsyncMock(return_value=session)
    manager.__aenter__.return_value = manager
    monkeypatch.setattr(
        embeddings, "HttpClientSessionManager", MagicMock(return_value=manager)
    )

    generator = OpenRouterQueryEmbedding(
        QueryEmbeddingSettings(OPENROUTER_API_KEY="synthetic-test-key")
    )
    assert asyncio.run(generator.generate("Alzheimer disease")) == pytest.approx(
        [0.6, 0.8]
    )
    session.post.assert_called_once_with(
        "/api/v1/embeddings",
        headers={"Authorization": "Bearer synthetic-test-key"},
        json={
            "model": "liquid/lfm-2.5-embedding-350m:free",
            "input": "Alzheimer disease",
            "encoding_format": "float",
        },
    )
    session.get.assert_not_called()


def test_query_service_uses_one_embedding_and_existing_retrieval_methods(monkeypatch):
    generate = AsyncMock(return_value=[0.6, 0.8])
    monkeypatch.setattr(
        query, "OpenRouterQueryEmbedding", lambda: SimpleNamespace(generate=generate)
    )
    track = SimpleNamespace(semantic_search_by_embedding=AsyncMock(return_value=[]))
    gene = SimpleNamespace(semantic_search_by_embedding=AsyncMock(return_value=[]))
    monkeypatch.setattr(query, "Track", track)
    monkeypatch.setattr(query, "Gene", gene)
    session = object()
    service = query.QueryEndpointService(
        context=SimpleNamespace(database_session=session),
        parameters=Parameters(query="Alzheimer", limit=5),
        response_config=ResponseConfiguration(
            record_model=SearchMatch, response_model=RecordResponse
        ),
    )
    assert asyncio.run(service.semantic_search()) == []
    generate.assert_awaited_once_with("Alzheimer")
    for model in (track, gene):
        model.semantic_search_by_embedding.assert_awaited_once_with(
            session,
            "Alzheimer",
            [0.6, 0.8],
            limit=5,
        )

    generate.side_effect = RuntimeError("Provider unavailable")
    with pytest.raises(RuntimeError, match="Provider unavailable"):
        asyncio.run(service.semantic_search())
    assert track.semantic_search_by_embedding.await_count == 1
    assert gene.semantic_search_by_embedding.await_count == 1
