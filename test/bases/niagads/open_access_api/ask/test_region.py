"""Region prototype exposes the API contract without database retrieval."""

import pytest


@pytest.mark.parametrize(
    "params",
    [
        {"region": "chr19:100-200"},
        {"chr": "19", "start": 100, "end": 200},
    ],
)
def test_valid_region_reports_not_implemented(client, params):
    response = client.get("/record/region/associations", params=params)
    assert response.status_code == 501
    assert "ORM" in response.json()["detail"]


@pytest.mark.parametrize(
    "params",
    [
        {"region": "chr1:1-5", "chr": "1", "start": 1, "end": 5},
        {"chr": "1", "start": 1},
        {"region": "chr1:20-10"},
        {"region": "chr1:0-10"},
        {"region": "BAD"},
    ],
)
def test_invalid_region_input_fails_before_placeholder(client, params):
    assert client.get("/record/region/associations", params=params).status_code == 422
