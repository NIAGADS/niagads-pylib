import asyncio
from typing import List, Optional
from fastapi.exceptions import RequestValidationError
from collections import ChainMap
from itertools import groupby
from operator import itemgetter

from niagads.utils.list import cumulative_sum, chunker

from api.common.enums import CacheKeyQualifier, ResponseContent, CacheNamespace
from api.common.helpers import Parameters, ResponseConfiguration, RouteHelper
from api.models.base_models import SerializableModel

from .constants import CACHEDB_PARALLEL_TIMEOUT, TRACKS_PER_API_REQUEST_LIMIT
from .enums import FILERApiEndpoint
from .services import MetadataQueryService, ApiWrapperService
from ..dependencies.parameters import InternalRequestParameters
from ..models.track_metadata_cache import Track

import logging
LOGGER = logging.getLogger(__name__)

    
class FILERRouteHelper(RouteHelper):  
    
    def __init__(self, managers: InternalRequestParameters, responseConfig: ResponseConfiguration, params: Parameters):
        super().__init__(managers, responseConfig, params)
        self._managers: InternalRequestParameters = managers


    async def __page_data_query(self, trackSummary: dict):
        """ calculate expected result size, number of pages; 
            returns current set of paged tracks"""
        
        # check to see if pagination has been cached
        cacheKey = self._managers.cacheKey.query_cache + CacheKeyQualifier.CURSOR
        cursors = await self._managers.internalCache.get(cacheKey, 
            namespace=CacheNamespace.QUERY_CACHE, 
            timeout=CACHEDB_PARALLEL_TIMEOUT)
        
        if cursors is not None:
            # cursors were cached, exctract the current cursor from the cache
            self.initialize_pagination()
            currentCursor = cursors[self._pagination.page]
        
        else: # determine pagination cursors
            # calculate cumulative sum of expected hits per track 
            sortedTrackSummary = sorted(trackSummary, key = lambda item: item['num_overlaps'], reverse=True)
            cumulativeSum = cumulative_sum([t['num_overlaps'] for t in sortedTrackSummary])
            self._resultSize = cumulativeSum[-1] # last element is total number of hits      
    
            self.initialize_pagination()
            
            if self._resultSize <= self._pageSize:
                # last track, last record
                cursors = [f'{sortedTrackSummary[-1]['track_id']}_{cumulativeSum[-1]}']    
            else: # one cursor per page
                cursors = [f'{sortedTrackSummary[0]['track_id']}_0']
                p: int # annotated type hint
                for p in range(2, self._pagination.total_num_pages):
                    pRange = self.page_array(p + 1)
                    trackIndex = next((index for index, counts in enumerate(cumulativeSum) if counts >= pRange.start))
        
        pagedTracks = None
        if self._resultSize <= self._pageSize:
            pagedTracks = [t['track_id'] for t in trackSummary]
        
        else:
            pageRange = self.page_array()
            
            
            # cursor = self.cursor()
            
            # NOTE: () in the `next` returns an iterator instead of a list 
            # (i.e. instead of []) for dictionary comprehension
            pageStartIndex = next((index for index, counts in enumerate(cumulativeSum) if counts >= pageRange.start))
            pageEndIndex = len(cumulativeSum) - 1 if pageRange.end == self._resultSize \
                else next((index for index, counts in enumerate(cumulativeSum) if counts >= pageRange.end))       
    
            pagedTracks = [t['track_id'] for t in sortedTrackSummary[pageStartIndex:pageEndIndex]]
        
        return pagedTracks

    
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


    async def __get_track_data_task(self, tracks, assembly: str, span: str, countsOnly: bool, cacheKey: str):
        cacheKey += ','.join(tracks)
        result = await self._managers.internalCache.get(cacheKey, namespace=CacheNamespace.FILER_EXTERNAL_API, timeout=CACHEDB_PARALLEL_TIMEOUT)
        if result is None:   
            result = await ApiWrapperService(self._managers.apiClientSession).get_track_hits(tracks, span, assembly, countsOnly=countsOnly)
            await self._managers.internalCache.set(cacheKey, result, namespace=CacheNamespace.FILER_EXTERNAL_API, timeout=CACHEDB_PARALLEL_TIMEOUT)
        return result


    async def get_track_data(self, validate=True): 
        isCached = True # assuming true from the start
        cacheKey = self._managers.cacheKey
        
        result = await self._managers.internalCache.get(cacheKey.internal, namespace=cacheKey.namespace)

        if result is None:
            isCached = False
            
            summarize = self._responseConfig.content == ResponseContent.SUMMARY
            countsOnly = self._responseConfig.content == ResponseContent.COUNTS or summarize == True 
            
            tracks = self._parameters.get('_paged_tracks', self._parameters.get('track'))
            tracks = tracks.split(',') if isinstance(tracks, str) else tracks
            tracks = sorted(tracks) # best for caching
            
            assembly = self._parameters.get('assembly')
            if validate or assembly is None: # for internal helper calls, don't always need to validate; already done
                assembly = await self.__validate_tracks(tracks)         
                
            cacheKey = f'/{FILERApiEndpoint.OVERLAPS}?countsOnly={countsOnly}&span={self._parameters.span}&tracks=' 
            cacheKey = cacheKey.replace(':', '_')
            
            if countsOnly: # summarize & counts only do not need to be chunked
                result = await self.__get_track_data_task(tracks, assembly, self._parameters.span, countsOnly, cacheKey)
            
                if summarize: # summarize doesn't need to be chunked b/c DB query
                    metadata: List[Track] = await self.get_track_metadata(rawResponse=ResponseContent.SUMMARY)
                    result = self.__generate_track_overlap_summary(metadata, result)
                    # this step will be cached in __generate_response
                    
            else: # make parallel calls for large lists of tracks
                chunks = chunker(tracks, TRACKS_PER_API_REQUEST_LIMIT, returnIterator=True)
                tasks = [self.__get_track_data_task(c, assembly, self._parameters.span, countsOnly, cacheKey) for c in chunks]
                chunkedResults = await asyncio.gather(*tasks, return_exceptions=False)
                result = []
                for r in chunkedResults:
                    result.extend(r)
                
        return await self.generate_response(result, isCached=isCached)


    def __generate_track_overlap_summary(self, metadata: List[Track], data):
        result = self.__merge_track_lists(
            [t.serialize(promoteObjs=True) for t in metadata], 
            data if isinstance(data[0], dict) else [t.serialize() for t in data])
        result = sorted(result, key = lambda item: item['num_overlaps'], reverse=True)
        return result


    async def get_track_metadata(self, rawResponse=False):
        """ fetch track metadata; expects a list of track identifiers in the parameters"""
        isCached = True # assuming true from the start
        cacheKey = self._managers.cacheKey.internal
        if rawResponse:
            cacheKey = cacheKey + CacheKeyQualifier.RAW
        
        result = await self._managers.internalCache.get(
            cacheKey, 
            namespace=self._managers.cacheKey.namespace)
        
        if result is None:
            isCached = False
        
            tracks = self._parameters.get('_paged_tracks',  self._parameters.get('track'))
            tracks = tracks.split(',') if isinstance(tracks, str) else tracks
            tracks = sorted(tracks) # best for caching & pagination
            
            result = await MetadataQueryService(self._managers.session).get_track_metadata(tracks)
            
            if not rawResponse:
                self._resultSize = len(result)
                pageResponse = self.initialize_pagination(raiseError=False)
                if pageResponse:
                    pageRange = self.page_array()
                    result = result[pageRange.start:pageRange.end]
            
        if rawResponse:
            # cache the raw response
            await self._managers.internalCache.set(
                cacheKey,
                result, 
                namespace=self._managers.cacheKey.namespace)
            
            return result

        return await self.generate_response(result, isCached=isCached)


    # FIXME: not sure if this will ever need a "rawResponse"
    async def get_collection_track_metadata(self, rawResponse=False):
        """ fetch track metadata for a specific collection """
        isCached = True # assuming true from the start
        cacheKey = self._managers.cacheKey.internal
        if rawResponse:
            cacheKey = cacheKey + '&raw'    
        
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
                    pageRange = self.page_array()
                    result = result[pageRange.start:pageRange.end]
            
        if rawResponse:
            # cache the raw response
            await self._managers.internalCache.set(
                cacheKey,
                result, 
                namespace=self._managers.cacheKey.namespace)
            
            return result

        return await self.generate_response(result, isCached=isCached)
    

    async def search_track_metadata(self, rawResponse:Optional[ResponseContent] = None):
        """ retrieve track metadata based on filter/keyword searches """
        isCached = True # assuming true from the start
        cacheKey = self._managers.cacheKey.internal
        content = self._responseConfig.content
        
        if rawResponse is not None:
            content = rawResponse
            cacheKey = self._managers.cacheKey.internal_raw + '&internal=' + str(rawResponse)    
        
        result = await self._managers.internalCache.get(
            cacheKey, 
            namespace=self._managers.cacheKey.namespace)
                
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
                    cacheKey,
                    result, 
                    namespace=self._managers.cacheKey.namespace)
                return result
            
        return await self.generate_response(result, isCached=isCached) \
            if rawResponse is None else result


    async def search_track_data(self):
        result = await self._managers.internalCache.get(self._managers.cacheKey.internal, namespace=self._managers.cacheKey.namespace)
        if result is not None: # just return the cached response
            return await self.generate_response(result, isCached=True)
        
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
        informativeTracks = await self._managers.internalCache.get(cacheKey, namespace=CacheNamespace.FILER_EXTERNAL_API)
        if informativeTracks is None:
            # get tracks with data in the region
            informativeTracks = await ApiWrapperService(self._managers.apiClientSession) \
                .get_informative_tracks(self._parameters.span, self._parameters.assembly)
            # cache this response from the FILER Api
            await self._managers.internalCache.set(cacheKey, informativeTracks, namespace=CacheNamespace.FILER_EXTERNAL_API)
        
        # TODO: cache this?
        # filter for tracks that match the filter
        matchingTrackIds = [t.track_id for t in matchingTracks] if rawResponse != ResponseContent.IDS else matchingTracks
        informativeTrackIds = [t['track_id'] for t in informativeTracks] 
        targetTrackIds = list(set(matchingTrackIds).intersection(informativeTrackIds))
        targetTracks = [t for t in informativeTracks if t['track_id'] in targetTrackIds]
        
        # generate paged response for IDS, COUNTS, SUMMARY
        # this avoids a second call to the FILER API just to get counts
        if not self._responseConfig.content == ResponseContent.FULL:
            self._resultSize = len(targetTracks)
            self.initialize_pagination()
            pageRange = self.page_array()
            
            match self._responseConfig.content:
                case ResponseContent.IDS:
                    # to ensure pagination order, need to sort by counts and re-extract the IDS
                    result = sorted(targetTracks, key = lambda item: item['num_overlaps'], reverse=True)
                    result = [t['track_id'] for t in result[pageRange.start:pageRange.end]]
                    return await self.generate_response(result)
                
                case ResponseContent.COUNTS:
                    # sort by counts to ensure pagination order
                    result = sorted(targetTracks, key = lambda item: item['num_overlaps'], reverse=True)
                    return await self.generate_response(result[pageRange.start:pageRange.end])
                
                case ResponseContent.SUMMARY: 
                    # generate track overlap sorts by counts after merging with the metadata
                    metadata = [t for t in matchingTracks if t.track_id in targetTrackIds]
                    result = self.__generate_track_overlap_summary(metadata, targetTracks)
                    return await self.generate_response(result[pageRange.start:pageRange.end])
                
                case _:
                    raise RuntimeError('Invalid response content specified')
            
        # page the FULL data response
        pagedTracks = self.__page_data_query(targetTracks)
        self._parameters.update('_paged_tracks', pagedTracks)
        
        return await self.get_track_data(validate=False)

    