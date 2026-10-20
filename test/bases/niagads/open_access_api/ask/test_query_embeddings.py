"""Query the configured gene and track embeddings through the API."""

import pytest
from niagads.common.search.models.record import SearchMatch
from niagads.common.search.types import MatchType
from niagads.common.types import Entity


@pytest.mark.parametrize("entity", [Entity.GENE, Entity.TRACK])
def test_query_embeddings(client, entity):
    response = client.get(
        f"/query/{entity.value}s",
        params={"query": "Alzheimer disease", "limit": 5},
    )

    assert response.status_code == 200, response.text
    records = response.json()["data"]
    assert records
    assert len(records) <= 5
    for record in records:
        match = SearchMatch(matched_record_id=record["id"], **record)
        assert match.matched_record_type == entity
        assert match.match_type == MatchType.SEMANTIC
        assert match.matched_record_id
        assert match.score is not None
