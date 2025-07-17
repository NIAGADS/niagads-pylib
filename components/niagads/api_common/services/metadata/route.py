from typing import Optional

from niagads.database.schemas.dataset.track import TrackDataStore
from niagads.api_common.models.services.cache import CacheKeyQualifier
from niagads.api_common.parameters.internal import InternalRequestParameters
from niagads.api_common.parameters.response import ResponseContent
from niagads.api_common.services.metadata.query import MetadataQueryService
from niagads.api_common.services.route import (
    Parameters,
    ResponseConfiguration,
    RouteHelperService,
)


class MetadataRouteHelperService(RouteHelperService):
    """RouteHelperService extended w/Metadata queries"""

    def __init__(
        self,
        managers: InternalRequestParameters,
        response_config: ResponseConfiguration,
        params: Parameters,
        data_store=[TrackDataStore.SHARED],
    ):
        super().__init__(managers, response_config, params)
        self._data_store = data_store

    async def get_track_metadata(self, raw_response=False):
        """fetch track metadata; expects a list of track identifiers in the parameters"""
        is_cached = True  # assuming true from the start
        cache_key = self._managers.cache_key.encrypt()
        if raw_response:
            cache_key += CacheKeyQualifier.RAW

        result = await self._managers.cache.get(
            cache_key, namespace=self._managers.cache_key.namespace
        )

        if result is None:
            is_cached = False

            tracks = self._parameters.get("_tracks", self._parameters.get("track"))
            tracks = tracks.split(",") if isinstance(tracks, str) else tracks
            tracks = sorted(tracks)  # best for caching & pagination

            result = await MetadataQueryService(
                self._managers.session, data_store=self._data_store
            ).get_track_metadata(tracks, response_type=self._response_config.content)

            if not raw_response:
                self._result_size = len(result)
                is_paged = self.initialize_pagination()
                if is_paged:
                    sliceRange = self.slice_result_by_page()
                    result = result[sliceRange.start : sliceRange.end]

        if raw_response:
            # cache the raw response
            await self._managers.cache.set(
                cache_key, result, namespace=self._managers.cache_key.namespace
            )

            return result

        return await self.generate_response(result, is_cached=is_cached)

    # FIXME: not sure if this will ever need a "raw_response"
    async def get_collection_track_metadata(self, raw_response=False):
        """fetch track metadata for a specific collection"""
        is_cached = True  # assuming true from the start
        cache_key = self._managers.cache_key.encrypt()
        if raw_response:
            cache_key += CacheKeyQualifier.RAW + "_" + str(raw_response)

        result = await self._managers.cache.get(
            cache_key, namespace=self._managers.cache_key.namespace
        )

        if result is None:
            is_cached = False

            result = await MetadataQueryService(
                self._managers.session,
                self._managers.request_data,
                self._data_store,
            ).get_collection_track_metadata(
                self._parameters.get("collection"),
                self._parameters.get("track"),
                response_type=self._response_config.content,
            )

            if not raw_response:
                self._result_size = len(result)
                is_paged = self.initialize_pagination()
                if is_paged:
                    sliceRange = self.slice_result_by_page()
                    result = result[sliceRange.start : sliceRange.end]

        if raw_response:
            # cache the raw response
            await self._managers.cache.set(
                cache_key, result, namespace=self._managers.cache_key.namespace
            )
            return result

        return await self.generate_response(result, is_cached=is_cached)

    async def search_track_metadata(
        self, raw_response: Optional[ResponseContent] = None
    ):
        """retrieve track metadata based on filter/keyword searches"""
        cache_key = self._managers.cache_key.encrypt()
        content = self._response_config.content

        if raw_response is not None:
            content = raw_response
            cache_key += CacheKeyQualifier.RAW + "_" + str(raw_response)

        result = await self._managers.cache.get(
            cache_key, namespace=self._managers.cache_key.namespace
        )

        if result is not None:
            return (
                result
                if raw_response
                else await self.generate_response(result, is_cached=True)
            )

        offset = None
        limit = None
        if raw_response is None:
            # get counts to either return or determine pagination
            result = await MetadataQueryService(
                self._managers.session, data_store=self._data_store
            ).query_track_metadata(
                self._parameters.get("assembly"),
                self._parameters.get("filter", None),
                self._parameters.get("keyword", None),
                ResponseContent.COUNTS,
            )

            if content == ResponseContent.COUNTS:
                return await self.generate_response(result, is_cached=False)

            self._result_size = result["num_tracks"]
            is_paged = self.initialize_pagination()
            if is_paged:  # will return true if model can be paged and page is valid
                offset = self.offset()
                limit = self._pageSize

        result = await MetadataQueryService(
            self._managers.session, data_store=self._data_store
        ).query_track_metadata(
            self._parameters.get("assembly"),
            self._parameters.get("filter", None),
            self._parameters.get("keyword", None),
            content,
            limit,
            offset,
        )

        if raw_response is None:
            return await self.generate_response(result, is_cached=False)
        else:  # cache the raw response before returning
            await self._managers.cache.set(
                cache_key, result, namespace=self._managers.cache_key.namespace
            )
            return result

    async def get_shard(self):
        cache_key = self._managers.cache_key.encrypt()

        result = await self._managers.cache.get(
            cache_key, namespace=self._managers.cache_key.namespace
        )

        if result is not None:
            return await self.generate_response(result, is_cached=True)

        # TODO: validate track

        # result = await MetadataQueryService(self._managers.session, self._managers.requestData, self._dataStore) \
        #         .get_shard(self._parameters.track, self._parameters.chr,
        #            response_type=self._response_config.content)

        raise NotImplementedError("Query helper not yet implemented")
