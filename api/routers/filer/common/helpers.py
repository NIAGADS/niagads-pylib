import asyncio
from typing import List, Optional
from fastapi.exceptions import RequestValidationError
from collections import ChainMap
from itertools import groupby
from operator import itemgetter

from niagads.utils.list import cumulative_sum, chunker
from pydantic import BaseModel, computed_field

from api.common.enums import CacheKeyQualifier, ResponseContent, CacheNamespace
from api.common.helpers import Parameters, ResponseConfiguration, RouteHelper, PaginationCursor
from api.common.types import Range
from api.models.base_models import CacheKeyDataModel
from api.routers.filer.models.bed_features import BEDFeature

from .constants import CACHEDB_PARALLEL_TIMEOUT, TRACKS_PER_API_REQUEST_LIMIT
from .enums import FILERApiEndpoint
from .services import FILERApiDataResponse, TrackOverlap, MetadataQueryService, ApiWrapperService, sort_track_overlaps
from ..dependencies.parameters import InternalRequestParameters
from ..models.track_metadata_cache import Track

import logging
LOGGER = logging.getLogger(__name__)


class FILERPaginationCursor(BaseModel):
    tracks: List[str]
    start: PaginationCursor
    end: PaginationCursor


class FILERRouteHelper(RouteHelper):  
    
    def __init__(self, managers: InternalRequestParameters, responseConfig: ResponseConfiguration, params: Parameters):
        super().__init__(managers, responseConfig, params)
        self._managers: InternalRequestParameters = managers


    async def __initialize_data_query_pagination(self, trackOverlaps: List[TrackOverlap]) -> FILERPaginationCursor:
        """ calculate expected result size, number of pages; 
            determines and caches cursor-based pagination
            
            pagination determined as follows:
            
            1. sort track summary in DESC order by number of data points
            2. calculate cumulative sum to estimate result size
            3. create array of `ordered_track_index`:`offset` pairs defining the end point for the current page
                (start point is cursor[page - 1], with cursor[0] always being `0:0`)
            
            returns current set of pagedTracks, and start/end points for slicing within track results
        """
        # sort the track summary
        sortedTrackOverlaps: List[TrackOverlap] = sort_track_overlaps(trackOverlaps)
        
        # generate cache keys
        noPageCacheKey = self._managers.cacheKey.no_page()
        cursorCacheKey = CacheKeyDataModel.encrypt_key(noPageCacheKey + CacheKeyQualifier.CURSOR)
        rsCacheKey = CacheKeyDataModel.encrypt_key(noPageCacheKey + CacheKeyQualifier.RESULT_SIZE)
        
        # check to see if pagination has been cached
        cursors = await self._managers.internalCache.get(cursorCacheKey, 
            namespace=CacheNamespace.QUERY_CACHE, timeout=CACHEDB_PARALLEL_TIMEOUT)
        self._resultSize = await self._managers.internalCache.get(rsCacheKey,
                namespace=CacheNamespace.QUERY_CACHE, timeout=CACHEDB_PARALLEL_TIMEOUT)
        
        # if either is uncached, the data may be out of sync so recalculate cache size
        if cursors is None or self._resultSize is None: 
            # calculate cumulative sum of expected hits per track 
            cumulativeSum = cumulative_sum([t.num_overlaps for t in sortedTrackOverlaps])
            
            self._resultSize = cumulativeSum[-1] # last element is total number of hits      
            await self._managers.internalCache.set(rsCacheKey, self._resultSize,
                namespace=CacheNamespace.QUERY_CACHE, timeout=CACHEDB_PARALLEL_TIMEOUT)
            
            self.initialize_pagination() # need total number of pages to find cursors
            
            cursors = ['0:0']
            if self._resultSize > self._pageSize:  # figure out page cursors
                for p in range(1, self._pagination.total_num_pages):
                    sliceRange = self.slice_result_by_page(p)

                    for index, counts in enumerate(cumulativeSum):
                        if counts > sliceRange.end: 
                            offset = sliceRange.end 
                            cursors.append(f'{index}:{offset}')
                            break
                        
                        """
                        if counts >= sliceRange.start and counts < sliceRange.end:
                            diff = sliceRange.end - cumulativeSum[index]
                            offset = sortedTrackOverlaps[index].num_overlaps - diff
                            cursors.append(f'{index}:{offset}')
                            break
                        """
                        
            # end of final page is always the last rack, last feature
            cursors.append(f'{len(sortedTrackOverlaps)-1}:{sortedTrackOverlaps[-1].num_overlaps}') 

            # cache the pagination cursor
            await self._managers.internalCache.set(cursorCacheKey, cursors,
                namespace=CacheNamespace.QUERY_CACHE, timeout=CACHEDB_PARALLEL_TIMEOUT)

        else: # initialize from cached pagination
            self.initialize_pagination()
        
        startTrackIndex, startOffset = [int(x) for x in cursors[self._pagination.page - 1].split(':')]
        endTrackIndex, endIndex = [int (x) for x in cursors[self._pagination.page].split(':')]
        pagedTracks = [t.track_id for t in sortedTrackOverlaps[startTrackIndex:endTrackIndex + 1]]
        
        return FILERPaginationCursor(tracks=pagedTracks,
            # cursor list & start/endTrackIndex is based on all tracks; need to adjust for pagedTrack slice
            start=PaginationCursor(key=0, offset=startOffset),
            end=PaginationCursor(key=endTrackIndex - startTrackIndex, offset=endIndex))
    
    
    def __merge_track_lists(self, trackList1, trackList2):
        matched = groupby(sorted(trackList1 + trackList2, key=itemgetter('track_id')), itemgetter('track_id'))
        combinedLists = [dict(ChainMap(*g)) for k, g in matched]
        return combinedLists
    

    async def __validate_tracks(self, tracks: List[str]):
        """ by setting validate=True, the service runs .validate_tracks before validating the genome build"""
        assembly = await MetadataQueryService(self._managers.session).get_genome_build(tracks, validate=True)
        if isinstance(assembly, dict):
            raise RequestValidationError(f'Tracks map to multiple assemblies; please query GRCh37 and GRCh38 data independently')
        return assembly


    def __page_data_result(self, cursor: FILERPaginationCursor, response: List[FILERApiDataResponse]) -> List[BEDFeature]:
        
        # sort the response by the cursor pagedTracks so the track order is correct
        # FILER currently processes sequentially so this is unecessary but if updated
        # to process in parallel, it will be required
        sortedResponse = sorted(response, key=lambda  x:cursor.tracks == x.Identifier)
        
        result: List[BEDFeature] = [] 
        for trackIndex, track in enumerate(sortedResponse):
            sliceStart = cursor.start.offset if trackIndex == cursor.start.key \
                else None
            sliceEnd = cursor.end.offset if  trackIndex == cursor.end.key \
                else None
            
            features: List[BEDFeature] = track.features[sliceStart:sliceEnd]
            for f in features:
                f.add_track(track.Identifier)
                result.append(f)
                
        return result
    

    async def __get_track_data_task(self, tracks, assembly: str, span: str, countsOnly: bool, cacheKey: str):
        cacheKey += ','.join(tracks)
        result = await self._managers.internalCache.get(cacheKey, namespace=CacheNamespace.FILER_EXTERNAL_API, timeout=CACHEDB_PARALLEL_TIMEOUT)
        if result is None:   
            result = await ApiWrapperService(self._managers.apiClientSession).get_track_hits(tracks, span, assembly, countsOnly=countsOnly)
            await self._managers.internalCache.set(cacheKey, result, namespace=CacheNamespace.FILER_EXTERNAL_API, timeout=CACHEDB_PARALLEL_TIMEOUT)
        return result


    async def get_paged_track_data(self, trackOverlaps:List[TrackOverlap], validate=True):
        cacheKey = self._managers.cacheKey
        
        result = await self._managers.internalCache.get(cacheKey.key, namespace=cacheKey.namespace)
        if result is not None:
            return await self.generate_response(result, isCached=True)
        
        cursor: FILERPaginationCursor = await self.__initialize_data_query_pagination(trackOverlaps)
        
        assembly = self._parameters.get('assembly')
        if validate or assembly is None: # for internal helper calls, don't always need to validate; already done
            assembly = await self.__validate_tracks(cursor.tracks)     
            
        cacheKey = f'/{FILERApiEndpoint.OVERLAPS}?countsOnly=False&span={self._parameters.span}&tracks=' 
        cacheKey = cacheKey.replace(':', '_')
        
        chunks = chunker(cursor.tracks, TRACKS_PER_API_REQUEST_LIMIT, returnIterator=True)
        tasks = [self.__get_track_data_task(c, assembly, self._parameters.span, False, cacheKey) for c in chunks]
        chunkedResults = await asyncio.gather(*tasks, return_exceptions=False)
        
        response: List[FILERApiDataResponse] = []
        for r in chunkedResults:
            response = response + r

        result = self.__page_data_result(cursor, response)
        
        return await self.generate_response(result, isCached=False)
    
        
    async def get_track_data(self, validate=True): 
        """ if trackSummary is set, then fetches from the summary not from a parameter"""
        
        result = await self._managers.internalCache.get(self._managers.cacheKey.key,
            namespace=self._managers.cacheKey.namespace)
        if result is not None:
            return await self.generate_response(result, isCached=True)

        tracks = self._parameters.get('track') 
        tracks = tracks.split(',') if isinstance(tracks, str) else tracks
        tracks = sorted(tracks) # best for caching
        
        assembly = self._parameters.get('assembly')
        if validate or assembly is None: # for internal helper calls, don't always need to validate; already done
            assembly = await self.__validate_tracks(tracks)         
    
        # get counts - needed for full pagination, counts only, summary
        cacheKey = f'/{FILERApiEndpoint.OVERLAPS}?countsOnly=true&span={self._parameters.span}&tracks=' 
        cacheKey = cacheKey.replace(':', '_')
        trackOverlaps = await self.__get_track_data_task(tracks, assembly, self._parameters.span, True, cacheKey)
        
        if self._responseConfig.content == ResponseContent.FULL:
            return await self.get_paged_track_data(trackOverlaps, validate=validate)

        # to ensure pagination order, need to sort by counts
        sortedTrackOverlaps = sort_track_overlaps(trackOverlaps)
        self._resultSize = len(sortedTrackOverlaps)
        self.initialize_pagination()
        sliceRange = self.slice_result_by_page()
        
        match self._responseConfig.content:
            case ResponseContent.IDS:
                result = [t['track_id'] for t in sortedTrackOverlaps[sliceRange.start:sliceRange.end]]
                return await self.generate_response(result)
            
            case ResponseContent.COUNTS:
                # sort by counts to ensure pagination order
                return await self.generate_response(sortedTrackOverlaps[sliceRange.start:sliceRange.end])
            
            case ResponseContent.SUMMARY: 
                metadata: List[Track] = await self.get_track_metadata(rawResponse=ResponseContent.SUMMARY)
                result = self.__generate_track_overlap_summary(metadata, sortedTrackOverlaps)
                return await self.generate_response(result[sliceRange.start:sliceRange.end])
            
            case _:
                raise RuntimeError('Invalid response content specified')

    def __generate_track_overlap_summary(self, metadata: List[Track], data):
        result = self.__merge_track_lists(
            [t.serialize(promoteObjs=True) for t in metadata], 
            data if isinstance(data[0], dict) else [t.serialize() for t in data])
        result = sorted(result, key = lambda item: item['num_overlaps'], reverse=True)
        return result


    async def get_track_metadata(self, rawResponse=False):
        """ fetch track metadata; expects a list of track identifiers in the parameters"""
        isCached = True # assuming true from the start
        cacheKey = self._managers.cacheKey.key
        if rawResponse:
            cacheKey = cacheKey + CacheKeyQualifier.RAW
        
        result = await self._managers.internalCache.get(
            cacheKey, namespace=self._managers.cacheKey.namespace)
        
        if result is None:
            isCached = False
        
            tracks = self._parameters.get('_tracks',  self._parameters.get('track'))
            tracks = tracks.split(',') if isinstance(tracks, str) else tracks
            tracks = sorted(tracks) # best for caching & pagination
            
            result = await MetadataQueryService(self._managers.session).get_track_metadata(tracks)
            
            if not rawResponse:
                self._resultSize = len(result)
                pageResponse = self.initialize_pagination(raiseError=False)
                if pageResponse:
                    sliceRange = self.slice_result_by_page()
                    result = result[sliceRange.start:sliceRange.end]
            
        if rawResponse:
            # cache the raw response
            await self._managers.internalCache.set(
                cacheKey, result, 
                namespace=self._managers.cacheKey.namespace)
            
            return result

        return await self.generate_response(result, isCached=isCached)


    # FIXME: not sure if this will ever need a "rawResponse"
    async def get_collection_track_metadata(self, rawResponse=False):
        """ fetch track metadata for a specific collection """
        isCached = True # assuming true from the start
        cacheKey = self._managers.cacheKey.key
        if rawResponse:
            cacheKey = cacheKey + CacheKeyQualifier.RAW + '_' + str(rawResponse)    
        
        result = await self._managers.internalCache.get(
            cacheKey, 
            namespace=self._managers.cacheKey.namespace)
        
        if result is None:
            isCached = False
        
            result = await MetadataQueryService(self._managers.session).get_collection_track_metadata(self._parameters.collection)
            
            if not rawResponse:
                self._resultSize = len(result)
                pageResponse = self.initialize_pagination(raiseError=False)
                if pageResponse:
                    sliceRange = self.slice_result_by_page()
                    result = result[sliceRange.start:sliceRange.end]
            
        if rawResponse:
            # cache the raw response
            await self._managers.internalCache.set(
                cacheKey, result, 
                namespace=self._managers.cacheKey.namespace)
            
            return result

        return await self.generate_response(result, isCached=isCached)
    

    async def search_track_metadata(self, rawResponse:Optional[ResponseContent] = None):
        """ retrieve track metadata based on filter/keyword searches """
        isCached = True # assuming true from the start
        cacheKey = self._managers.cacheKey.key
        content = self._responseConfig.content
        
        if rawResponse is not None:
            content = rawResponse
            cacheKey = cacheKey + CacheKeyQualifier.RAW + '_' + str(rawResponse)    
        
        result = await self._managers.internalCache.get(
            cacheKey, namespace=self._managers.cacheKey.namespace)
                
        if result is None:
            isCached = False
            offset = None
            limit = None
            
            if content != ResponseContent.IDS and rawResponse is None:
                # get counts to either return or determine pagination
                result = await MetadataQueryService(self._managers.session) \
                    .query_track_metadata(self._parameters.assembly, 
                        self._parameters.get('filter', None), self._parameters.get('keyword', None), ResponseContent.COUNTS)
            
                if content == ResponseContent.COUNTS:
                    return await self.generate_response(result, isCached=isCached)
                
                self._resultSize = result['track_count']
                pageResponse = self.initialize_pagination(raiseError=False)
                if pageResponse: # will return true if model can be paged and page is valid
                    offset = self.offset()
                    limit = self._pageSize
                
            result = await MetadataQueryService(self._managers.session) \
                .query_track_metadata(self._parameters.assembly, 
                    self._parameters.get('filter', None), self._parameters.get('keyword', None), 
                    content, limit, offset)

            if rawResponse is not None:
                # cache the raw response
                await self._managers.internalCache.set(
                    cacheKey, result, 
                    namespace=self._managers.cacheKey.namespace)
                return result
            
        return await self.generate_response(result, isCached=isCached) \
            if rawResponse is None else result


    async def search_track_data(self):
        result = await self._managers.internalCache.get(self._managers.cacheKey.key, namespace=self._managers.cacheKey.namespace)
        if result is not None: # just return the cached response
            return await self.generate_response(result, isCached=True)
    
        hasMetadataFilters = self._parameters.keyword is not None or self._parameters.filter is not None
        
        # note: we test for metadata filters twice so we don't
        # need to do the informativeTrack lookup if metadata filters return nothing
        
        # apply metadata filters, if valid
        if hasMetadataFilters:
            # get list of tracks that match the search filter
            rawResponse = ResponseContent.IDS
            if self._responseConfig.content == ResponseContent.SUMMARY:
                rawResponse = ResponseContent.SUMMARY
            matchingTracks: List[Track] = await self.search_track_metadata(rawResponse=rawResponse) 
            
            if len(matchingTracks) == 0:
                return await self.generate_response([], isCached=False)
        
        
        # get informative tracks from the FILER API & cache
        cacheKey = f'/{FILERApiEndpoint.INFORMATIVE_TRACKS}?genomeBuild={self._parameters.assembly}&span={self._parameters.span}' 
        cacheKey = cacheKey.replace(':','_')
        informativeTrackOverlaps: List[TrackOverlap] = await self._managers.internalCache.get(cacheKey, namespace=CacheNamespace.FILER_EXTERNAL_API)
        if informativeTrackOverlaps is None:
            informativeTrackOverlaps = await ApiWrapperService(self._managers.apiClientSession) \
                .get_informative_tracks(self._parameters.span, self._parameters.assembly)
            await self._managers.internalCache.set(cacheKey, informativeTrackOverlaps, namespace=CacheNamespace.FILER_EXTERNAL_API)
            
        if len(informativeTrackOverlaps) == 0:
            return await self.generate_response([], isCached=False)
        
        targetTrackOverlaps = informativeTrackOverlaps
        
        if hasMetadataFilters:
            # filter for tracks that match the filter
            matchingTrackIds = [t.track_id for t in matchingTracks] if rawResponse != ResponseContent.IDS else matchingTracks
            informativeTrackIds = [t.track_id for t in informativeTrackOverlaps] 
            targetTrackIds = list(set(matchingTrackIds).intersection(informativeTrackIds))
            targetTrackOverlaps: List[TrackOverlap] = [t for t in informativeTrackOverlaps if t.track_id in targetTrackIds]
        
        if self._responseConfig.content == ResponseContent.FULL:
            return await self.get_paged_track_data(targetTrackOverlaps)
        
        # to ensure pagination order, need to sort by counts
        result: List[TrackOverlap] = sort_track_overlaps(targetTrackOverlaps)
        self._resultSize = len(result)
        self.initialize_pagination()
        sliceRange = self.slice_result_by_page()
        
        match self._responseConfig.content:
            case ResponseContent.IDS:
                result = [t.track_id for t in result[sliceRange.start:sliceRange.end]]
                return await self.generate_response(result)
            
            case ResponseContent.COUNTS:
                # sort by counts to ensure pagination order
                return await self.generate_response(result[sliceRange.start:sliceRange.end])
            
            case ResponseContent.SUMMARY: 
                metadata:List[Track] = [t for t in matchingTracks if t.track_id in targetTrackIds]
                result = self.__generate_track_overlap_summary(metadata, result)
                return await self.generate_response(result[sliceRange.start:sliceRange.end])
            
            case _:
                raise RuntimeError('Invalid response content specified')
