"""Region prototype exposes the API contract without database retrieval."""

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from niagads.api.common.exception_handlers import add_not_implemented_exception_handler
from niagads.open_access_api.routes.records.region import router


@pytest.fixture
def client():
    app = FastAPI()
    app.include_router(router)
    add_not_implemented_exception_handler(app)
    return TestClient(app)


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


def test_region_declares_existing_response_and_pagination_contract(client):
    operation = client.get("/openapi.json").json()["paths"][
        "/record/region/associations"
    ]["get"]
    assert operation["operationId"] == "getRegionAssociations"
    assert operation["tags"] == ["Region"]
    assert operation["x-status"] == "planned"
    names = {p["name"] for p in operation["parameters"]}
    assert {"region", "chr", "start", "end", "page", "format", "content"} <= names
    assert "RecordResponse" in str(operation["responses"]["200"])
