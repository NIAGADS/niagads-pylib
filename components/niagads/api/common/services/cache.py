from typing import Any, Optional, Tuple

from niagads.api.common.models.context.cache import (
    CacheKeyDataModel,
    CacheKeyQualifier,
    CacheNamespace,
)
from niagads.cache.core import KeyDBCacheManager

# FIXME - streamline to remove get_/set_view_response


class CacheService:

    def __init__(self, cache: KeyDBCacheManager, cache_key: CacheKeyDataModel):
        self._cache = cache
        self._cache_key = cache_key

    @property
    def cache_key(self) -> CacheKeyDataModel:
        return self._cache_key

    async def get(self, key: str, namespace: CacheNamespace):
        return await self._cache.get(key, namespace=namespace)

    async def set(self, key: str, value: Any, namespace: CacheNamespace):
        await self._cache.set(key, value, namespace=namespace)

    async def get_response(self) -> Optional[Any]:
        return await self.get(
            self._cache_key.encrypt(),
            namespace=self._cache_key.namespace,
        )

    async def set_response(self, response: Any):
        await self.set(
            self._cache_key.encrypt(),
            response,
            namespace=self._cache_key.namespace,
        )

    async def get_view_response(self, view) -> Tuple[str, Optional[Any]]:
        cache_key = CacheKeyDataModel.encrypt_key(
            self._cache_key.key + str(CacheKeyQualifier.VIEW) + str(view)
        )
        response = await self.get(cache_key, namespace=CacheNamespace.LAYOUT)
        return cache_key, response

    async def set_view_response(self, view, response: Any):
        cache_key = CacheKeyDataModel.encrypt_key(
            self._cache_key.key + str(CacheKeyQualifier.VIEW) + str(view)
        )
        await self.set(cache_key, response, namespace=CacheNamespace.LAYOUT)
