import asyncio
from typing import List, Union
from fastapi import HTTPException
from niagads.exceptions.core import ValidationError
from collections import ChainMap
from itertools import groupby
from operator import itemgetter

from niagads.database.genomicsdb.schemas.dataset.track import Track, TrackDataStore
from niagads.database.session import DatabaseSessionManager
from niagads.assembly.core import GenomicFeatureType
from niagads.api_common.models.features.bed import BEDFeature
from niagads.api_common.models.features.genomic import GenomicFeature
from niagads.api_common.models.services.cache import (
    CacheKeyDataModel,
    CacheKeyQualifier,
    CacheNamespace,
)
from niagads.api_common.models.datasets.track import TrackResultSize
from niagads.api_common.parameters.internal import InternalRequestParameters
from niagads.api_common.parameters.response import ResponseContent
from niagads.api_common.services.metadata.query import MetadataQueryService
from niagads.api_common.services.metadata.route import (
    MetadataRouteHelperService,
)
from niagads.api_common.services.route import (
    PaginationCursor as PaginationCursor,
    Parameters,
    ResponseConfiguration,
)
from niagads.filer_api.services.wrapper import (
    ApiWrapperService,
    FILERApiDataResponse,
    FILERApiEndpoint,
)
from niagads.utils.list import cumulative_sum, chunker
from pydantic import BaseModel
from sqlalchemy import bindparam, text

FILER_HTTP_CLIENT_TIMEOUT = 60
CACHEDB_PARALLEL_TIMEOUT = 30
TRACKS_PER_API_REQUEST_LIMIT = 50


class TrackPaginationCursor(BaseModel):
    tracks: List[str]
    start: PaginationCursor
    end: PaginationCursor


class FILERRouteHelper(MetadataRouteHelperService):

    def __init__(
        self,
        managers: InternalRequestParameters,
        responseConfig: ResponseConfiguration,
        params: Parameters,
    ):
        super().__init__(
            managers,
            responseConfig,
            params,
            [TrackDataStore.FILER, TrackDataStore.SHARED],
        )

    async def __initialize_data_query_pagination(
        self, trackResultSummary: List[TrackResultSize]
    ) -> TrackPaginationCursor:
        """calculate expected result size, number of pages;
        determines and caches cursor-based pagination

        pagination determined as follows:

        1. sort track summary in DESC order by number of data points
        2. calculate cumulative sum to estimate result size
        3. create array of `ordered_track_index`:`offset` pairs defining the end point for the current page
            (start point is cursor[page - 1], with cursor[0] always being `0:0`)

        returns current set of pagedTracks, and start/end points for slicing within track results
        """
        # sort the track summary
        sortedTrackResultSummary: List[TrackResultSize] = TrackResultSize.sort(
            trackResultSummary
        )

        # generate cache keys
        noPageCacheKey = self._managers.cache_key.no_page()
        cursorCacheKey = CacheKeyDataModel.encrypt_key(
            noPageCacheKey + CacheKeyQualifier.CURSOR
        )
        rs_cache_key = CacheKeyDataModel.encrypt_key(
            noPageCacheKey + CacheKeyQualifier.RESULT_SIZE
        )

        # check to see if pagination has been cached
        cursors = await self._managers.cache.get(
            cursorCacheKey,
            namespace=CacheNamespace.QUERY_CACHE,
            timeout=CACHEDB_PARALLEL_TIMEOUT,
        )
        self._result_size = await self._managers.cache.get(
            rs_cache_key,
            namespace=CacheNamespace.QUERY_CACHE,
            timeout=CACHEDB_PARALLEL_TIMEOUT,
        )

        # if either is uncached, the data may be out of sync so recalculate cache size
        if cursors is None or self._result_size is None:
            cumulativeSum = cumulative_sum(
                [t.num_results for t in sortedTrackResultSummary]
            )
            self._result_size = cumulativeSum[
                -1
            ]  # last element is total number of hits

            await self._managers.cache.set(
                rs_cache_key,
                self._result_size,
                namespace=CacheNamespace.QUERY_CACHE,
                timeout=CACHEDB_PARALLEL_TIMEOUT,
            )

            self.initialize_pagination()  # need total number of pages to find cursors

            cursors = ["0:0"]
            if self._result_size > self._pageSize:  # figure out page cursors
                residualRecords = 0
                priorTrackIndex = 0
                offset = 0
                for p in range(1, self._pagination.total_num_pages):
                    sliceRange = self.slice_result_by_page(p)
                    for index, counts in enumerate(cumulativeSum):
                        if counts > sliceRange.end:  # end of page
                            offset = (
                                offset + self._pageSize
                                if priorTrackIndex == index
                                else self._pageSize - residualRecords
                            )
                            cursors.append(f"{index}:{offset}")

                            residualRecords = (
                                sortedTrackResultSummary[index].num_results - offset
                            )
                            priorTrackIndex = index

                            break

            # end of final page is always the last track, last feature
            cursors.append(
                f"{len(sortedTrackResultSummary)-1}:{sortedTrackResultSummary[-1].num_results}"
            )

            # cache the pagination cursor
            await self._managers.cache.set(
                cursorCacheKey,
                cursors,
                namespace=CacheNamespace.QUERY_CACHE,
                timeout=CACHEDB_PARALLEL_TIMEOUT,
            )

        else:  # initialize from cached pagination
            self.initialize_pagination()

        startTrackIndex, startOffset = [
            int(x) for x in cursors[self._pagination.page - 1].split(":")
        ]
        endTrackIndex, endIndex = [
            int(x) for x in cursors[self._pagination.page].split(":")
        ]
        pagedTracks = [
            t.track_id
            for t in sortedTrackResultSummary[startTrackIndex : endTrackIndex + 1]
        ]

        return TrackPaginationCursor(
            tracks=pagedTracks,
            # cursor list & start/endTrackIndex is based on all tracks; need to adjust for pagedTrack slice
            start=PaginationCursor(key=0, offset=startOffset),
            end=PaginationCursor(key=endTrackIndex - startTrackIndex, offset=endIndex),
        )

    def __merge_track_lists(self, trackList1, trackList2):
        matched = groupby(
            sorted(trackList1 + trackList2, key=itemgetter("track_id")),
            itemgetter("track_id"),
        )
        combinedLists = [dict(ChainMap(*g)) for k, g in matched]
        return combinedLists

    async def __validate_tracks(self, tracks: List[str]):
        """by setting validate=True, the service runs .validate_tracks before validating the genome build"""
        assembly = await MetadataQueryService(
            self._managers.session, data_store=self._data_store
        ).get_genome_build(tracks, validate=True)
        if isinstance(assembly, dict):
            raise ValidationError(
                f"Tracks map to multiple assemblies; please query GRCh37 and GRCh38 data independently"
            )
        return assembly

    def __page_data_result(
        self, cursor: TrackPaginationCursor, data: List[FILERApiDataResponse]
    ) -> List[BEDFeature]:

        # sort the response by the cursor pagedTracks so the track order is correct
        # FILER currently processes sequentially so this is unecessary but if updated
        # to process in parallel, it will be required
        sortedData = sorted(data, key=lambda x: cursor.tracks == x.Identifier)

        result: List[BEDFeature] = []
        for trackIndex, track in enumerate(sortedData):
            sliceStart = cursor.start.offset if trackIndex == cursor.start.key else None
            sliceEnd = cursor.end.offset if trackIndex == cursor.end.key else None

            features: List[BEDFeature] = track.features[sliceStart:sliceEnd]
            for f in features:
                f.add_track(track.Identifier)
                result.append(f)

        return result

    async def __get_track_data_task(
        self, tracks: List[str], assembly: str, span: str, countsOnly: bool
    ):
        cache_key = CacheKeyDataModel.encrypt_key(
            f"/{FILERApiEndpoint.OVERLAPS}?assembly={assembly}&countsOnly={countsOnly}"
            + f"&span={span}&tracks={','.join(tracks)}"
        )
        result = await self._managers.cache.get(
            cache_key,
            namespace=CacheNamespace.EXTERNAL_API,
            timeout=CACHEDB_PARALLEL_TIMEOUT,
        )
        if result is None:
            result = await ApiWrapperService(
                self._managers.api_client_session
            ).get_track_hits(tracks, span, assembly, countsOnly=countsOnly)
            await self._managers.cache.set(
                cache_key,
                result,
                namespace=CacheNamespace.EXTERNAL_API,
                timeout=CACHEDB_PARALLEL_TIMEOUT,
            )
        return result

    async def __get_gene_qtl_data_task(self, track: str, gene: str):
        cache_key = CacheKeyDataModel.encrypt_key(
            f"/{FILERApiEndpoint.GENE_QTLS}?" + f"&gene={gene}&track={track}"
        )
        result = await self._managers.cache.get(
            cache_key,
            namespace=CacheNamespace.EXTERNAL_API,
            timeout=CACHEDB_PARALLEL_TIMEOUT,
        )
        if result is None:
            result = await ApiWrapperService(
                self._managers.api_client_session
            ).get_gene_qtls(track, gene)
            await self._managers.cache.set(
                cache_key,
                result,
                namespace=CacheNamespace.EXTERNAL_API,
                timeout=CACHEDB_PARALLEL_TIMEOUT,
            )
        return result

    async def __get_paged_track_data(
        self, trackResultSummary: List[TrackResultSize], span=None, validate=True
    ):

        result = await self._managers.cache.get(
            self._managers.cache_key.encrypt(),
            namespace=self._managers.cache_key.namespace,
        )
        if result is not None:
            return await self.generate_response(result, is_cached=True)

        cursor: TrackPaginationCursor = await self.__initialize_data_query_pagination(
            trackResultSummary
        )

        assembly = self._parameters.get("assembly")
        if (
            validate or assembly is None
        ):  # for internal helper calls, don't always need to validate; already done
            assembly = await self.__validate_tracks(cursor.tracks)

        chunks = chunker(
            cursor.tracks, TRACKS_PER_API_REQUEST_LIMIT, returnIterator=True
        )
        tasks = [
            self.__get_track_data_task(
                c, assembly, span if span else self._parameters.get("span"), False
            )
            for c in chunks
        ]
        chunkedResults = await asyncio.gather(*tasks, return_exceptions=False)

        data: List[FILERApiDataResponse] = []
        for r in chunkedResults:
            data = data + r

        result = self.__page_data_result(cursor, data)

        return await self.generate_response(result, is_cached=False)

    async def get_track_data(self, validate=True):
        """if AbridgedTrack is set, then fetches from the summary not from a parameter"""

        cachedResponse = await self._get_cached_response()
        if cachedResponse is not None:
            return cachedResponse

        tracks = self._parameters.get("track")
        tracks = tracks.split(",") if isinstance(tracks, str) else tracks
        tracks = sorted(tracks)  # best for caching

        assembly = self._parameters.get("assembly")
        if (
            validate or assembly is None
        ):  # for internal helper calls, don't always need to validate; already done
            assembly = await self.__validate_tracks(tracks)

        span = await self.get_feature_location(self._parameters.get("span"))

        # get counts - needed for full pagination, counts only, summary
        trackResultSummary = await self.__get_track_data_task(
            tracks, assembly, span, True
        )

        if self._response_config.content == ResponseContent.FULL:
            return await self.__get_paged_track_data(
                trackResultSummary, span=span, validate=validate
            )

        # to ensure pagination order, need to sort by counts
        sortedTrackResultSummary: List[TrackResultSize] = TrackResultSize.sort(
            trackResultSummary
        )
        self._result_size = len(sortedTrackResultSummary)
        self.initialize_pagination()
        sliceRange = self.slice_result_by_page()

        match self._response_config.content:
            case ResponseContent.IDS:
                result = [
                    t["track_id"]
                    for t in sortedTrackResultSummary[sliceRange.start : sliceRange.end]
                ]
                return await self.generate_response(result)

            case ResponseContent.COUNTS:
                # sort by counts to ensure pagination order
                return await self.generate_response(
                    sortedTrackResultSummary[sliceRange.start : sliceRange.end]
                )

            case ResponseContent.BRIEF | ResponseContent.URLS:
                metadata: List[Track] = await self.get_track_metadata(
                    raw_response=ResponseContent.BRIEF
                )
                summary = self.__generate_track_overlap_summary(
                    metadata, sortedTrackResultSummary
                )
                result = (
                    [t["url"] for t in summary[sliceRange.start : sliceRange.end]]
                    if self._response_config.content == ResponseContent.URLS
                    else summary[sliceRange.start : sliceRange.end]
                )
                return await self.generate_response(result)

            case _:
                raise RuntimeError("Invalid response content specified")

    def __generate_track_overlap_summary(
        self, metadata: List[Track], data: Union[List[dict], List[TrackResultSize]]
    ):
        result = self.__merge_track_lists(
            [t.model_dump() for t in metadata],
            (
                data
                if isinstance(data[0], dict)
                else [t.model_dump(by_alias=False) for t in data]
            ),
        )
        result = sorted(result, key=lambda item: item["num_results"], reverse=True)
        return result

    async def search_track_data(self):
        cachedResponse = await self._get_cached_response()
        if cachedResponse is not None:
            return cachedResponse

        hasMetadataFilters = (
            self._parameters.get("keyword") is not None
            or self._parameters.get("filter") is not None
        )

        # note: we test for metadata filters twice so we don't
        # need to do the informativeTrack lookup if metadata filters return nothing

        # apply metadata filters, if valid
        if hasMetadataFilters:
            # get list of tracks that match the search filter
            raw_response = ResponseContent.IDS
            if self._response_config.content == ResponseContent.BRIEF:
                raw_response = ResponseContent.BRIEF
            matchingTracks: List[Track] = await self.search_track_metadata(
                raw_response=raw_response
            )

            if len(matchingTracks) == 0:
                self._managers.request_data.add_message(
                    "No tracks meet the specified metadata filter criteria."
                )
                return await self.generate_response([], is_cached=False)

        span = await self.get_feature_location(self._parameters.get("span"))

        # get informative tracks from the FILER API & cache
        cache_key = f"/{FILERApiEndpoint.INFORMATIVE_TRACKS}?assembly={self._parameters.get('assembly')}&span={span}"
        cache_key = CacheKeyDataModel.encrypt_key(cache_key.replace(":", "_"))

        informativeTrackOverlaps: List[TrackResultSize] = (
            await self._managers.cache.get(
                cache_key, namespace=CacheNamespace.EXTERNAL_API
            )
        )
        if informativeTrackOverlaps is None:
            informativeTrackOverlaps = await ApiWrapperService(
                self._managers.api_client_session
            ).get_informative_tracks(span, self._parameters.get("assembly"))
            await self._managers.cache.set(
                cache_key,
                informativeTrackOverlaps,
                namespace=CacheNamespace.EXTERNAL_API,
            )

        if len(informativeTrackOverlaps) == 0:
            self._managers.request_data.add_message(
                "No overlapping features found in the query region."
            )
            return await self.generate_response([], is_cached=False)

        targetTrackResultSize = informativeTrackOverlaps

        if hasMetadataFilters:
            # filter for tracks that match the filter
            matchingTrackIds = (
                [t.track_id for t in matchingTracks]
                if raw_response != ResponseContent.IDS
                else matchingTracks
            )
            informativeTrackIds = [t.track_id for t in informativeTrackOverlaps]
            targetTrackIds = list(
                set(matchingTrackIds).intersection(informativeTrackIds)
            )
            targetTrackResultSize: List[TrackResultSize] = [
                t for t in informativeTrackOverlaps if t.track_id in targetTrackIds
            ]

        if self._response_config.content == ResponseContent.FULL:
            return await self.__get_paged_track_data(targetTrackResultSize, span=span)

        # to ensure pagination order, need to sort by counts
        result: List[TrackResultSize] = TrackResultSize.sort(targetTrackResultSize)
        self._result_size = len(result)
        self.initialize_pagination()
        sliceRange = self.slice_result_by_page()

        match self._response_config.content:
            case ResponseContent.IDS:
                result = [t.track_id for t in result[sliceRange.start : sliceRange.end]]
                return await self.generate_response(result)

            case ResponseContent.COUNTS:
                # sort by counts to ensure pagination order
                return await self.generate_response(
                    result[sliceRange.start : sliceRange.end]
                )

            case ResponseContent.BRIEF | ResponseContent.URLS:
                metadata: List[Track] = [
                    t for t in matchingTracks if t.track_id in targetTrackIds
                ]
                summary = self.__generate_track_overlap_summary(metadata, result)
                result = (
                    [t["url"] for t in summary[sliceRange.start : sliceRange.end]]
                    if self._response_config.content == ResponseContent.URLS
                    else summary[sliceRange.start : sliceRange.end]
                )
                return await self.generate_response(result)

            case _:
                raise RuntimeError("Invalid response content specified")

    async def get_feature_qtls(self):
        cachedResponse = await self._get_cached_response()
        if cachedResponse is not None:
            return cachedResponse

        assembly = await self.__validate_tracks([self._parameters.track])

        feature: GenomicFeature = self._parameters.location

        match feature.feature_type:
            case GenomicFeatureType.GENE:
                if feature.feature_id.startswith("ENSG"):
                    raise NotImplementedError(
                        f"Mapping through Ensembl IDS not yet implemented"
                    )
                data: FILERApiDataResponse = await self.__get_gene_qtl_data_task(
                    self._parameters.track, feature.feature_id
                )
                counts = TrackResultSize(
                    track_id=self._parameters.track, num_results=len(data.features)
                )

                if self._response_config.content == ResponseContent.COUNTS:
                    return await self.generate_response(counts)

                cursor: TrackPaginationCursor = (
                    await self.__initialize_data_query_pagination([counts])
                )
                result = self.__page_data_result(cursor, [data])
                return await self.generate_response(result, is_cached=False)

            case GenomicFeatureType.VARIANT:
                if feature.feature_id.startswith("rs"):
                    raise NotImplementedError(
                        f"Mapping through refSNP IDS not yet implemented"
                    )
                # chr:pos:ref-alt -> chr:pos-1:pos
                [chr, pos, ref, alt] = feature.feature_id.split(":")
                span = f"{chr}:{int(pos) - 1}-{pos}"
                self._parameters.update("assembly", assembly)
                self._parameters.update("span", span)
                return await self.get_track_data(validate=False)

            case GenomicFeatureType.REGION:
                self._parameters.update("assembly", assembly)
                self._parameters.update("span", feature.feature_id)
                return await self.get_track_data(validate=False)

            case _:
                raise NotImplementedError(
                    f"QTL queries for feature type ${str(feature.feature_type)} not yet implemented."
                )
