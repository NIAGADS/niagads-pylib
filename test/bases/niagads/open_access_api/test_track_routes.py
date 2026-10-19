import asyncio
from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest
from fastapi import FastAPI, Request
from httpx import ASGITransport, AsyncClient
from niagads.api.common.models.context.cache import CacheKey, CacheNamespace
from niagads.api.common.models.context.request import RequestDetails
from niagads.database.genomicsdb.schema.dataset.track import Track
from niagads.open_access_api.dependencies import OpenAccessEndpointContext
from niagads.open_access_api.routes.records.track import router


async def track_context(request: Request):
    return request.app.state.track_context


@pytest.fixture
def track_app(monkeypatch):
    application = FastAPI()
    application.include_router(router)
    context = SimpleNamespace(
        database_session=AsyncMock(),
        request_data=RequestDetails(
            request_id="track-test", endpoint="/record/track", parameters={}
        ),
        cache_key=CacheKey(key="/record/track", namespace=CacheNamespace.GENOMICS),
        cache_manager=SimpleNamespace(
            get=AsyncMock(return_value=None), set=AsyncMock()
        ),
    )
    record = {
        "source_id": "track-a",
        "name": "Track A",
        "provenance": {"data_source": "NIAGADS"},
        "file_properties": {
            "file_name": "track-a.bed",
            "md5sum": "a" * 32,
            "file_size": 100,
        },
    }
    lookup = AsyncMock(return_value={"track-a": [record], "missing": []})
    monkeypatch.setattr(Track, "retrieve_records", lookup)
    application.state.track_context = context
    application.dependency_overrides[OpenAccessEndpointContext] = track_context
    return application, context, lookup


async def request_track(application, path, params):
    async with AsyncClient(
        transport=ASGITransport(app=application), base_url="http://test"
    ) as client:
        return await client.get(path, params=params)


@pytest.mark.parametrize("content", ["full", "summary"])
@pytest.mark.parametrize("multiple", [True, False])
def test_track_records(track_app, content, multiple):
    application, context, lookup = track_app
    path = "/record/track/" if multiple else "/record/track/track-a"
    params = {"content": content}
    if multiple:
        params["ids"] = "track-a,missing"
    else:
        lookup.return_value = {"track-a": lookup.return_value["track-a"]}

    response = asyncio.run(request_track(application, path, params))

    assert response.status_code == 200, response.text
    data = response.json()["data"]
    records = data["track-a"] if multiple else data
    assert records[0]["id"] == "track-a"
    assert records[0]["name"] == "Track A"
    if content == "full":
        assert records[0]["provenance"]["data_source"] == "NIAGADS"
    else:
        assert records[0]["data_source"] == "NIAGADS"
    if multiple:
        assert data["missing"] == []
    lookup.assert_awaited_once_with(
        context.database_session,
        ["track-a", "missing"] if multiple else ["track-a"],
    )


@pytest.mark.parametrize("multiple", [True, False])
def test_track_cache_hit(track_app, multiple):
    application, context, lookup = track_app
    record = {"id": "cached-track", "name": "Cached Track"}
    data = {"cached-track": [record]} if multiple else [record]
    context.cache_manager.get.return_value = {"data": data, "pagination": None}
    path = "/record/track/" if multiple else "/record/track/cached-track"
    params = {"content": "summary"}
    if multiple:
        params["ids"] = "cached-track"

    response = asyncio.run(request_track(application, path, params))

    assert response.status_code == 200, response.text
    result = response.json()["data"]
    records = result["cached-track"] if multiple else result
    assert records[0]["id"] == "cached-track"
    lookup.assert_not_awaited()


def test_missing_track(track_app):
    application, _, lookup = track_app
    lookup.return_value = {"missing": []}

    response = asyncio.run(request_track(application, "/record/track/missing", {}))

    assert response.status_code == 404
