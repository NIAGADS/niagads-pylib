from typing import Optional

from niagads.database.models.metadata.track import TrackDataStore
from niagads.open_access_api_common.models.services.cache import CacheKeyQualifier
from niagads.open_access_api_common.parameters.internal import InternalRequestParameters
from niagads.open_access_api_common.parameters.response import ResponseContent
from niagads.open_access_api_common.services.metadata.query import MetadataQueryService
from niagads.open_access_api_common.services.route import (
    Parameters,
    ResponseConfiguration,
    RouteHelperService,
)


class MetadataRouteHelperService(RouteHelperService):
    """RouteHelperService extended w/Metadata queries"""

    def __init__(
        self,
        managers: InternalRequestParameters,
        responseConfig: ResponseConfiguration,
        params: Parameters,
        dataStore=[TrackDataStore.SHARED],
    ):
        super().__init__(managers, responseConfig, params)
        self._dataStore = dataStore

    async def get_track_metadata(self, rawResponse=False):
        """fetch track metadata; expects a list of track identifiers in the parameters"""
        isCached = True  # assuming true from the start
        cacheKey = self._managers.cacheKey.encrypt()
        if rawResponse:
            cacheKey += CacheKeyQualifier.RAW

        result = await self._managers.cache.get(
            cacheKey, namespace=self._managers.cacheKey.namespace
        )

        if result is None:
            isCached = False

            tracks = self._parameters.get("_tracks", self._parameters.get("track"))
            tracks = tracks.split(",") if isinstance(tracks, str) else tracks
            tracks = sorted(tracks)  # best for caching & pagination

            result = await MetadataQueryService(
                self._managers.session, dataStore=self._dataStore
            ).get_track_metadata(tracks, responseType=self._responseConfig.content)

            if not rawResponse:
                self._resultSize = len(result)
                pageResponse = self.initialize_pagination()
                if pageResponse:
                    sliceRange = self.slice_result_by_page()
                    result = result[sliceRange.start : sliceRange.end]

        if rawResponse:
            # cache the raw response
            await self._managers.cache.set(
                cacheKey, result, namespace=self._managers.cacheKey.namespace
            )

            return result

        return await self.generate_response(result, isCached=isCached)

    # FIXME: not sure if this will ever need a "rawResponse"
    async def get_collection_track_metadata(self, rawResponse=False):
        """fetch track metadata for a specific collection"""
        isCached = True  # assuming true from the start
        cacheKey = self._managers.cacheKey.encrypt()
        if rawResponse:
            cacheKey += CacheKeyQualifier.RAW + "_" + str(rawResponse)

        result = await self._managers.cache.get(
            cacheKey, namespace=self._managers.cacheKey.namespace
        )

        if result is None:
            isCached = False

            result = await MetadataQueryService(
                self._managers.session,
                self._managers.requestData,
                self._dataStore,
            ).get_collection_track_metadata(
                self._parameters.collection,
                self._parameters.track,
                responseType=self._responseConfig.content,
            )

            if not rawResponse:
                self._resultSize = len(result)
                pageResponse = self.initialize_pagination()
                if pageResponse:
                    sliceRange = self.slice_result_by_page()
                    result = result[sliceRange.start : sliceRange.end]

        if rawResponse:
            # cache the raw response
            await self._managers.cache.set(
                cacheKey, result, namespace=self._managers.cacheKey.namespace
            )
            return result

        return await self.generate_response(result, isCached=isCached)

    async def search_track_metadata(
        self, rawResponse: Optional[ResponseContent] = None
    ):
        """retrieve track metadata based on filter/keyword searches"""
        cacheKey = self._managers.cacheKey.encrypt()
        content = self._responseConfig.content

        if rawResponse is not None:
            content = rawResponse
            cacheKey += CacheKeyQualifier.RAW + "_" + str(rawResponse)

        result = await self._managers.cache.get(
            cacheKey, namespace=self._managers.cacheKey.namespace
        )

        if result is not None:
            return (
                result
                if rawResponse
                else await self.generate_response(result, isCached=True)
            )

        offset = None
        limit = None
        if rawResponse is None:
            # get counts to either return or determine pagination
            result = await MetadataQueryService(
                self._managers.session, dataStore=self._dataStore
            ).query_track_metadata(
                self._parameters.assembly,
                self._parameters.get("filter", None),
                self._parameters.get("keyword", None),
                ResponseContent.COUNTS,
            )

            if content == ResponseContent.COUNTS:
                return await self.generate_response(result, isCached=False)

            self._resultSize = result["num_tracks"]
            pageResponse = self.initialize_pagination()
            if pageResponse:  # will return true if model can be paged and page is valid
                offset = self.offset()
                limit = self._pageSize

        result = await MetadataQueryService(
            self._managers.session, dataStore=self._dataStore
        ).query_track_metadata(
            self._parameters.assembly,
            self._parameters.get("filter", None),
            self._parameters.get("keyword", None),
            content,
            limit,
            offset,
        )

        if rawResponse is None:
            return await self.generate_response(result, isCached=False)
        else:  # cache the raw response before returning
            await self._managers.cache.set(
                cacheKey, result, namespace=self._managers.cacheKey.namespace
            )
            return result

    async def get_shard(self):
        cacheKey = self._managers.cacheKey.encrypt()

        result = await self._managers.cache.get(
            cacheKey, namespace=self._managers.cacheKey.namespace
        )

        if result is not None:
            return await self.generate_response(result, isCached=True)

        # TODO: validate track

        # result = await MetadataQueryService(self._managers.session, self._managers.requestData, self._dataStore) \
        #         .get_shard(self._parameters.track, self._parameters.chr,
        #            responseType=self._responseConfig.content)

        raise NotImplementedError("Query helper not yet implemented")
