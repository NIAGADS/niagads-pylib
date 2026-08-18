import asyncio
from collections import ChainMap
from itertools import groupby
from operator import itemgetter
from typing import List, Union

from niagads.api.common.models.domain.entities.dataset.track import TrackResultMetrics
from niagads.api.common.models.domain.parameters.types import ResponseView
from niagads.api.common.models.service.cache import CacheKeyDataModel, CacheNamespace
from niagads.api.common.services.metadata.query import (
    MetadataQueryService,
    TrackDatabase,
)
from niagads.api.common.services.metadata.route import TrackMetadataEndpointService
from niagads.api.common.services.pagination import TrackDataPaginationCursor
from niagads.api.common.services.route import (
    RequestParameters,
    ResponseConfiguration,
)
from niagads.common.genomic.features.models import GenomicFeature, GenomicFeatureType
from niagads.database.genomicsdb.schema.dataset.track import Track
from niagads.exceptions.core import ValidationError
from niagads.filer_api.dependencies import FILEREndpointRequestParameters
from niagads.filer_api.services.client import (
    FILERApiDataResponse,
    FILERApiEndpoint,
    FILERClientService,
)
from niagads.filer_api.services.pagination import (
    FILERTrackDataPaginationService,
)
from niagads.utils.list import chunker

FILER_HTTP_CLIENT_TIMEOUT = 60
CACHEDB_PARALLEL_TIMEOUT = 30
TRACKS_PER_API_REQUEST_LIMIT = 50


class FILEREndpointService(TrackMetadataEndpointService):

    def __init__(
        self,
        managers: FILEREndpointRequestParameters,
        responseConfig: ResponseConfiguration,
        params: RequestParameters,
    ):

        super().__init__(
            managers, responseConfig, params, track_database=TrackDatabase.FILER
        )
        self._pagination_service = FILERTrackDataPaginationService(
            self._parameters,
            self._managers.cache_service,
            page_size=self.page_size,
        )

    def __merge_track_lists(self, trackList1, trackList2):
        matched = groupby(
            sorted(trackList1 + trackList2, key=itemgetter("id")),
            itemgetter("id"),
        )
        combinedLists = [dict(ChainMap(*g)) for k, g in matched]
        return combinedLists

    async def __validate_tracks(self, tracks: List[str]):
        """by setting validate=True, the service runs .validate_tracks before validating the genome build"""
        # FIXME: why is this instantiating a new query service instead of using self.__metadata_query_service
        assembly = await MetadataQueryService(
            self._managers.database_session, data_store=self._data_store
        ).get_genome_build(tracks, validate=True)
        if isinstance(assembly, dict):
            raise ValidationError(
                "Tracks map to multiple assemblies; please query GRCh37 and GRCh38 data independently"
            )
        return assembly

    async def __get_track_data_task(
        self, tracks: List[str], assembly: str, span: str, countsOnly: bool
    ):
        cache_key = CacheKeyDataModel.encrypt_key(
            f"/{FILERApiEndpoint.OVERLAPS}?genome_build={assembly}&countsOnly={countsOnly}"
            + f"&span={span}&tracks={','.join(tracks)}"
        )
        result = await self._managers.cache_service.get(
            cache_key, namespace=CacheNamespace.EXTERNAL_API
        )
        if result is None:
            result = await FILERClientService(
                self._managers.http_client_session
            ).get_track_hits(tracks, span, assembly, countsOnly=countsOnly)
            await self._managers.cache_service.set(
                cache_key, result, namespace=CacheNamespace.EXTERNAL_API
            )
        return result

    async def __get_gene_qtl_data_task(self, track: str, gene: str):
        cache_key = CacheKeyDataModel.encrypt_key(
            f"/{FILERApiEndpoint.GENE_QTLS}?" + f"&gene={gene}&track={track}"
        )
        result = await self._managers.cache_service.get(
            cache_key, namespace=CacheNamespace.EXTERNAL_API
        )
        if result is None:
            result = await FILERClientService(
                self._managers.http_client_session
            ).get_gene_qtls(track, gene)
            await self._managers.cache_service.set(
                cache_key, result, namespace=CacheNamespace.EXTERNAL_API
            )
        return result

    async def __get_paged_track_data(
        self, trackResultSummary: List[TrackResultMetrics], span=None, validate=True
    ):

        result = await self._managers.cache_service.get_response()
        if result is not None:
            return await self.generate_response(result, is_cached=True)

        cursor: TrackDataPaginationCursor = (
            await self._pagination_service.build_page_cursor(trackResultSummary)
        )

        assembly = self._parameters.get("genome_build")
        if (
            validate or assembly is None
        ):  # for internal helper calls, don't always need to validate; already done
            assembly = await self.__validate_tracks(cursor.tracks)

        chunks = chunker(
            cursor.tracks, TRACKS_PER_API_REQUEST_LIMIT, return_iterator=True
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

        result = self._pagination_service.page_data(cursor, data)

        return await self.generate_response(result, is_cached=False)

    async def get_track_data(self, validate=True):
        """if AbridgedTrack is set, then fetches from the summary not from a parameter"""

        cached_response = await self._managers.cache_service.get_response()
        if cached_response is not None:
            return await self.generate_response(cached_response, is_cached=True)

        tracks = self._parameters.get("track")
        tracks = tracks.split(",") if isinstance(tracks, str) else tracks
        tracks = sorted(tracks)  # best for caching

        assembly = self._parameters.get("genome_build")
        if (
            validate or assembly is None
        ):  # for internal helper calls, don't always need to validate; already done
            assembly = await self.__validate_tracks(tracks)

        span = await self.get_feature_location(self._parameters.get("span"))

        # get counts - needed for full pagination, counts only, summary
        trackResultSummary = await self.__get_track_data_task(
            tracks, assembly, span, True
        )

        if self._response_config.content == ResponseView.FULL:
            return await self.__get_paged_track_data(
                trackResultSummary, span=span, validate=validate
            )

        # to ensure pagination order, need to sort by counts
        sortedTrackResultSummary: List[TrackResultMetrics] = TrackResultMetrics.sort(
            trackResultSummary
        )
        self.set_result_size(len(sortedTrackResultSummary))
        self._pagination_service.initialize_pagination()
        sliceRange = self._pagination_service.slice_result_by_page()

        match self._response_config.content:
            case ResponseView.IDS:
                result = [
                    t["id"]
                    for t in sortedTrackResultSummary[sliceRange.start : sliceRange.end]
                ]
                return await self.generate_response(result)

            case ResponseView.COUNTS:
                # sort by counts to ensure pagination order
                return await self.generate_response(
                    sortedTrackResultSummary[sliceRange.start : sliceRange.end]
                )

            case ResponseView.BRIEF | ResponseView.URLS:
                metadata: List[Track] = await self.get_track_metadata(
                    raw_response=ResponseView.BRIEF
                )
                summary = self.__generate_track_overlap_summary(
                    metadata, sortedTrackResultSummary
                )
                result = (
                    [t["url"] for t in summary[sliceRange.start : sliceRange.end]]
                    if self._response_config.content == ResponseView.URLS
                    else summary[sliceRange.start : sliceRange.end]
                )
                return await self.generate_response(result)

            case _:
                raise RuntimeError("Invalid response content specified")

    def __generate_track_overlap_summary(
        self, metadata: List[Track], data: Union[List[dict], List[TrackResultMetrics]]
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
        cached_response = await self._managers.cache_service.get_response()
        if cached_response is not None:
            return await self.generate_response(cached_response, is_cached=True)

        hasMetadataFilters = (
            self._parameters.get("keyword") is not None
            or self._parameters.get("filter") is not None
        )

        # note: we test for metadata filters twice so we don't
        # need to do the informativeTrack lookup if metadata filters return nothing

        # apply metadata filters, if valid
        if hasMetadataFilters:
            # get list of tracks that match the search filter
            raw_response = ResponseView.IDS
            if self._response_config.content == ResponseView.BRIEF:
                raw_response = ResponseView.BRIEF
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
        cache_key = f"/{FILERApiEndpoint.INFORMATIVE_TRACKS}?genome_build={self._parameters.get('assembly')}&span={span}"
        cache_key = CacheKeyDataModel.encrypt_key(cache_key.replace(":", "_"))

        informativeTrackOverlaps: List[TrackResultMetrics] = (
            await self._managers.cache_service.get(
                cache_key, namespace=CacheNamespace.EXTERNAL_API
            )
        )
        if informativeTrackOverlaps is None:
            informativeTrackOverlaps = await FILERClientService(
                self._managers.http_client_session
            ).get_informative_tracks(span, self._parameters.get("genome_build"))
            await self._managers.cache_service.set(
                cache_key,
                informativeTrackOverlaps,
                namespace=CacheNamespace.EXTERNAL_API,
            )

        if len(informativeTrackOverlaps) == 0:
            self._managers.request_data.add_message(
                "No overlapping features found in the query region."
            )
            return await self.generate_response([], is_cached=False)

        targetTrackResultMetrics = informativeTrackOverlaps

        if hasMetadataFilters:
            # filter for tracks that match the filter
            matchingTrackIds = (
                [t.id for t in matchingTracks]
                if raw_response != ResponseView.IDS
                else matchingTracks
            )
            informativeTrackIds = [t.id for t in informativeTrackOverlaps]
            targetTrackIds = list(
                set(matchingTrackIds).intersection(informativeTrackIds)
            )
            targetTrackResultMetrics: List[TrackResultMetrics] = [
                t for t in informativeTrackOverlaps if t.id in targetTrackIds
            ]

        if self._response_config.content == ResponseView.FULL:
            return await self.__get_paged_track_data(
                targetTrackResultMetrics, span=span
            )

        # to ensure pagination order, need to sort by counts
        result: List[TrackResultMetrics] = TrackResultMetrics.sort(
            targetTrackResultMetrics
        )
        self.set_result_size(len(result))
        self._pagination_service.initialize_pagination()
        sliceRange = self._pagination_service.slice_result_by_page()

        match self._response_config.content:
            case ResponseView.IDS:
                result = [t.id for t in result[sliceRange.start : sliceRange.end]]
                return await self.generate_response(result)

            case ResponseView.COUNTS:
                # sort by counts to ensure pagination order
                return await self.generate_response(
                    result[sliceRange.start : sliceRange.end]
                )

            case ResponseView.BRIEF | ResponseView.URLS:
                metadata: List[Track] = [
                    t for t in matchingTracks if t.id in targetTrackIds
                ]
                summary = self.__generate_track_overlap_summary(metadata, result)
                result = (
                    [t["url"] for t in summary[sliceRange.start : sliceRange.end]]
                    if self._response_config.content == ResponseView.URLS
                    else summary[sliceRange.start : sliceRange.end]
                )
                return await self.generate_response(result)

            case _:
                raise RuntimeError("Invalid response content specified")

    async def get_feature_qtls(self):
        cached_response = await self._managers.cache_service.get_response()
        if cached_response is not None:
            return await self.generate_response(cached_response, is_cached=True)

        assembly = await self.__validate_tracks([self._parameters.track])

        feature: GenomicFeature = self._parameters.location

        match feature.feature_type:
            case GenomicFeatureType.GENE:
                if feature.feature_id.startswith("ENSG"):
                    raise NotImplementedError(
                        "Mapping through Ensembl IDS not yet implemented"
                    )
                data: FILERApiDataResponse = await self.__get_gene_qtl_data_task(
                    self._parameters.track, feature.feature_id
                )
                counts = TrackResultMetrics(
                    id=self._parameters.track, count=len(data.features)
                )

                if self._response_config.content == ResponseView.COUNTS:
                    return await self.generate_response(counts)

                cursor: TrackDataPaginationCursor = (
                    await self._pagination_service.build_page_cursor([counts])
                )
                result = self._pagination_service.page_data(cursor, [data])
                return await self.generate_response(result, is_cached=False)

            case GenomicFeatureType.VARIANT:
                if feature.feature_id.startswith("rs"):
                    raise NotImplementedError(
                        "Mapping through refSNP IDS not yet implemented"
                    )
                # chr:pos:ref-alt -> chr:pos-1:pos
                [chr, pos, ref, alt] = feature.feature_id.split(":")
                span = f"{chr}:{int(pos) - 1}-{pos}"
                self._parameters.update("genome_build", assembly)
                self._parameters.update("span", span)
                return await self.get_track_data(validate=False)

            case GenomicFeatureType.REGION:
                self._parameters.update("genome_build", assembly)
                self._parameters.update("span", feature.feature_id)
                return await self.get_track_data(validate=False)

            case _:
                raise NotImplementedError(
                    f"QTL queries for feature type ${str(feature.feature_type)} not yet implemented."
                )
