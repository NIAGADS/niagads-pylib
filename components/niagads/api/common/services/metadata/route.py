from typing import Optional

from niagads.api.common.models.domain.entities.dataset.collection import (
    CollectionMetadata,
)
from niagads.api.common.models.domain.entities.dataset.track import (
    TrackMetadata,
    TrackMetadataBrief,
)
from niagads.api.common.models.domain.parameters.internal import (
    InternalRequestParameters,
)

from niagads.api.common.models.domain.parameters.types import ResponseContent
from niagads.api.common.models.service.cache import CacheKeyQualifier
from niagads.api.common.services.metadata.query import (
    MetadataQueryService,
    TrackDatabase,
)
from niagads.api.common.services.route import (
    EndpointService,
    RequestParameters,
    ResponseConfiguration,
)

# FIXME: data_store -> is_filer_track


class TrackMetadataEndpointService(EndpointService):
    "Endpoint service for querying track metadata"

    def __init__(
        self,
        managers: InternalRequestParameters,
        response_config: ResponseConfiguration,
        params: RequestParameters,
        track_database: TrackDatabase = TrackDatabase.OPEN_ACCESS,
    ):
        super().__init__(managers, response_config, params)
        self.__metadata_query_service = MetadataQueryService(
            self._managers.database_session,
            self._managers.request_data,
            track_database=track_database,
        )

    async def __resolve_track_metadata_response_content(
        self, query_result: list[TrackMetadata]
    ):
        content = self._response_config.content
        if content == ResponseContent.FULL:
            track_records = [TrackMetadata(**t.model_dump()) for t in query_result]
        elif content == ResponseContent.BRIEF:
            track_records = [TrackMetadataBrief(**t.model_dump()) for t in query_result]
        elif content == ResponseContent.IDS:
            track_records = query_result
        elif content == ResponseContent.COUNTS:
            track_records = [{"num_results": len(query_result)}]
        elif content == ResponseContent.URLS:
            track_records = query_result

        return track_records

    async def get_track_metadata(self, raw_response=False):
        """fetch track metadata; expects a list of track identifiers in the parameters"""
        is_cached = True  # assuming true from the start
        cache_key = self._managers.cache_service.cache_key.encrypt()
        if raw_response:
            cache_key += CacheKeyQualifier.RAW

        cached_response = await self._managers.cache_service.get(
            cache_key, namespace=self._managers.cache_service.cache_key.namespace
        )

        if cached_response is None:
            is_cached = False

            tracks = self._parameters.get("_tracks", self._parameters.get("track"))
            tracks = tracks.split(",") if isinstance(tracks, str) else tracks
            tracks = sorted(tracks)  # best for caching & pagination

            query_result = await self.__metadata_query_service.get_track_metadata(
                tracks, response_type=self._response_config.content
            )

            if raw_response:
                # cache the raw response and return
                await self._managers.cache_service.set(
                    cache_key,
                    query_result,
                    namespace=self._managers.cache_service.cache_key.namespace,
                )
                return query_result

            else:
                track_records = self.__resolve_track_metadata_response_content(
                    query_result
                )

                self.set_result_size(len(query_result))
                is_paged = self._pagination_service.initialize_pagination()
                if is_paged:
                    sliceRange = self._pagination_service.slice_result_by_page()
                    paged_result = track_records[sliceRange.start : sliceRange.end]
                else:
                    paged_result = track_records

                return await self.generate_response(paged_result, is_cached=is_cached)

        return cached_response

    async def get_collections(self):
        is_cached = True  # assuming true from the start
        cache_key = self._managers.cache_service.cache_key.encrypt()

        result = await self._managers.cache_service.get(
            cache_key, namespace=self._managers.cache_service.cache_key.namespace
        )

        if result is None:
            is_cached = False

            result = await self.__metadata_query_service.get_collection(
                collection_id=self._parameters.get("collection_id")
            )
            collection_records = [CollectionMetadata(**c.model_dump()) for c in result]

        return await self.generate_response(collection_records, is_cached=is_cached)

    # FIXME: not sure if this will ever need a "raw_response"
    async def get_collection_track_metadata(self, raw_response=False):
        """fetch track metadata for a specific collection"""
        is_cached = True  # assuming true from the start
        cache_key = self._managers.cache_service.cache_key.encrypt()
        if raw_response:
            cache_key += CacheKeyQualifier.RAW + "_" + str(raw_response)

        cached_response = await self._managers.cache_service.get(
            cache_key, namespace=self._managers.cache_service.cache_key.namespace
        )

        if cached_response is None:
            is_cached = False

            query_result = (
                await self.__metadata_query_service.get_collection_track_metadata(
                    self._parameters.get("collection"),
                    self._parameters.get("track"),
                    response_type=self._response_config.content,
                )
            )

            if raw_response:
                # cache the raw response and return
                await self._managers.cache_service.set(
                    cache_key,
                    query_result,
                    namespace=self._managers.cache_service.cache_key.namespace,
                )
                return query_result

            else:
                track_records = self.__resolve_track_metadata_response_content(
                    query_result
                )

                self.set_result_size(len(query_result))
                is_paged = self._pagination_service.initialize_pagination()
                if is_paged:
                    sliceRange = self._pagination_service.slice_result_by_page()
                    paged_result = track_records[sliceRange.start : sliceRange.end]
                else:
                    paged_result = track_records

                return await self.generate_response(paged_result, is_cached=is_cached)

        return cached_response

    async def search_track_metadata(
        self, raw_response: Optional[ResponseContent] = None
    ):
        """retrieve track metadata based on filter/keyword searches"""
        cache_key = self._managers.cache_service.cache_key.encrypt()
        content = self._response_config.content

        if raw_response is not None:
            content = raw_response
            cache_key += CacheKeyQualifier.RAW + "_" + str(raw_response)

        result = await self._managers.cache_service.get(
            cache_key, namespace=self._managers.cache_service.cache_key.namespace
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
            result = await self.__metadata_query_service.query_track_metadata(
                self._parameters.get("genome_build"),
                self._parameters.get("filter", None),
                self._parameters.get("keyword", None),
                ResponseContent.COUNTS,
            )

            if content == ResponseContent.COUNTS:
                return await self.generate_response(result, is_cached=False)

            self.set_result_size(result["num_tracks"])
            is_paged = self._pagination_service.initialize_pagination()
            if is_paged:  # will return true if model can be paged and page is valid
                offset = self._pagination_service.offset()
                limit = self.page_size

        result = await self.__metadata_query_service.query_track_metadata(
            self._parameters.get("genome_build"),
            self._parameters.get("filter", None),
            self._parameters.get("keyword", None),
            content,
            limit,
            offset,
        )

        if raw_response is None:
            return await self.generate_response(result, is_cached=False)
        else:  # cache the raw response before returning
            await self._managers.cache_service.set(
                cache_key,
                result,
                namespace=self._managers.cache_service.cache_key.namespace,
            )
            return result

    async def get_shard(self):
        result = await self._managers.cache_service.get_response()

        if result is not None:
            return await self.generate_response(result, is_cached=True)

        # TODO: validate track

        # result = await MetadataQueryService(self._managers.session, self._managers.requestData, self._dataStore) \
        #         .get_shard(self._parameters.track, self._parameters.chr,
        #            response_type=self._response_config.content)

        raise NotImplementedError("Query helper not yet implemented")
