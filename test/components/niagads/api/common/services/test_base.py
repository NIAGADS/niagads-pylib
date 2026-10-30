import asyncio
from types import SimpleNamespace
from uuid import uuid4

import pytest
from aiocache import SimpleMemoryCache
from niagads.api.common.constants import DEFAULT_PAGE_SIZE
from niagads.api.common.models.context.cache import CacheKey, CacheNamespace
from niagads.api.common.models.context.request import Parameters, RequestDetails
from niagads.api.common.models.responses.records import RecordResponse
from niagads.api.common.services.base import BaseEndpointService


@pytest.mark.parametrize("cache_state", ["paged", "unpaged", "empty", "miss"])
def test_get_cached_response(cache_state):
    asyncio.run(check_cached_response(cache_state))


async def check_cached_response(cache_state):
    page = 1 if cache_state == "empty" else 2
    cache_key = CacheKey(
        key=f"/genes/{uuid4()}?page={page}", namespace=CacheNamespace.GENOMICS
    )
    cache = SimpleMemoryCache()
    request = RequestDetails(
        request_id="current-request", endpoint="/genes/", parameters={"page": page}
    )
    service = BaseEndpointService(
        context=SimpleNamespace(
            cache_key=cache_key, cache_manager=cache, request_data=request
        ),
        parameters=Parameters(page=page),
        response_config=SimpleNamespace(
            response_model=RecordResponse[RequestDetails], record_model=None
        ),
    )
    namespace = cache_key.namespace
    record = request.model_copy(update={"request_id": "record"})
    if cache_state == "paged":
        await cache.set(
            cache_key.encrypt(),
            RecordResponse[RequestDetails](request=request, data=[record]),
            namespace=namespace,
        )
    elif cache_state in ("unpaged", "empty"):
        await cache.set(
            cache_key.encrypt_key(cache_key.no_page()),
            [record] * (DEFAULT_PAGE_SIZE + 1) if cache_state == "unpaged" else [],
            namespace=namespace,
        )

    try:
        response = await service._get_cached_response()
        if cache_state == "miss":
            assert response is None
            return

        assert response is not None
        assert response.data == ([] if cache_state == "empty" else [record])
        if cache_state != "paged":
            assert response.pagination.page == page
            assert response.pagination.total_records == (
                DEFAULT_PAGE_SIZE + 1 if cache_state == "unpaged" else 0
            )
            cached_page = await cache.get(cache_key.encrypt(), namespace=namespace)
            assert cached_page == response
    finally:
        await cache.delete(cache_key.encrypt(), namespace=namespace)
        await cache.delete(
            cache_key.encrypt_key(cache_key.no_page()), namespace=namespace
        )
