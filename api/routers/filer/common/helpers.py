import asyncio
from typing import List
from fastapi.exceptions import RequestValidationError
from sqlalchemy.ext.asyncio import AsyncSession
from collections import ChainMap
from itertools import groupby
from operator import itemgetter

from niagads.utils.list import cumulative_sum, chunker

from api.common.enums import ResponseContent, CacheNamespace
from api.common.helpers import HelperParameters as __BaseHelperParameters, generate_response as __generate_response
from api.common.utils import get_attribute

from .constants import TRACKS_PER_API_REQUEST_LIMIT, DEFAULT_PAGE_SIZE, MAX_NUM_PAGES
from .enums import FILERApiEndpoint
from .services import MetadataQueryService, ApiWrapperService
from ..dependencies import InternalRequestParameters
from ..models.track_metadata_cache import Track

import logging
LOGGER = logging.getLogger(__name__)


class HelperParameters(__BaseHelperParameters):
    internal: InternalRequestParameters
    
class FILERRouteHelper():  
    __options: HelperParameters
    __pageSize: int = DEFAULT_PAGE_SIZE
    __offset: int = None
    __totalNumPages: int = None
    __resultSize: int = None

    def init(self, opts: HelperParameters):
        self.__options = opts
        
        
    def set_page_size(self, pageSize: int):
        self.__pageSize = pageSize
        
        
    def __set_total_num_pages(self):
        self.__totalNumPages = 1 if self.__resultSize < self.__pageSize \
            else next((p for p in range(1, MAX_NUM_PAGES) if (p - 1) * self.__pageSize > self.__resultSize)) - 1
        
    def __is_valid_page(self, page: int):
        """ test if the page is valid (w/in range of expected number of pages)"""     
        if page > self.__totalNumPages:
            raise RequestValidationError(f'Request `page` {page} does not exist; this query generates a maximum of {self.__totalNumPages} pages')
        
        return True
    
    def __page_metadata_query(self, page: int):
        """ calculate offset and total number of pages for pagination"""
        self.__set_total_num_pages()
        self.__is_valid_page()

        self.__offset = None if page == 1 else (page - 1) * self.__pageSize

        
    def __page_track_data_query(self, trackSummary: dict, page: int):
        """ calculate expected result size, number of pages; returns current set of paged tracks"""
        # returns pagedTrackIds, resultSize, numPages
        
        # calculate cumulative sum of expected hits per track 
        sortedTrackSummary = sorted(trackSummary, key = lambda item: item['num_overlaps'], reverse=True)
        cumulativeSum = cumulative_sum([t['num_overlaps'] for t in sortedTrackSummary])
        self.__resultSize = cumulativeSum[-1] # last element is total number of hits
        
        self.__set_total_num_pages()
        self.__is_valid_page()
        
        pagedTracks = None
        if self.__resultSize <= self.__pageSize and page == 1:
            return [t['track_id'] for t in trackSummary]
        
        minRecordRowIndex = (page - 1) * self.__pageSize
        maxRecordRowIndex = minRecordRowIndex + self.__pageSize
        if maxRecordRowIndex > expectedResultSize:
            maxRecordRowIndex = expectedResultSize
        
        
        # () returns an iterator instead of a list; i.e. []
        pageStartIndex = next((index for index, counts in enumerate(cumulativeSum) if counts >= minRecordRowIndex))
        pageEndIndex = len(cumulativeSum) - 1 if maxRecordRowIndex == expectedResultSize \
            else next((index for index, counts in enumerate(cumulativeSum) if counts >= maxRecordRowIndex)) - 1
        pagedTracks = [t['track_id'] for t in sortedTrackSummary[pageStartIndex:pageEndIndex]]
        
        return pagedTracks, expectedResultSize, expectedNumPages
        

    
    def __merge_track_lists(self, trackList1, trackList2):
        matched = groupby(sorted(trackList1 + trackList2, key=itemgetter('track_id')), itemgetter('track_id'))
        combinedLists = [dict(ChainMap(*g)) for k, g in matched]
        return combinedLists

    async def __validate_tracks(session: AsyncSession, tracks: List[str]):
        """ by setting validate=True, the service runs .validate_tracks before validating the genome build"""
        assembly = await MetadataQueryService(session).get_genome_build(tracks, validate=True)
        if isinstance(assembly, dict):
            raise RequestValidationError(f'Tracks map to multiple assemblies; please query GRCh37 and GRCh38 data independently')
        return assembly


    async def __get_track_data_task(tracks, assembly: str, span: str, countsOnly: bool, cacheKey: str, managers:InternalRequestParameters):
        cacheKey += ','.join(tracks)
        result = await managers.internalCache.get(cacheKey, namespace=CacheNamespace.FILER_EXTERNAL_API)
        if result is None:   
            result = await ApiWrapperService(managers.apiClientSession).get_track_hits(tracks, span, assembly, countsOnly=countsOnly)
            await managers.internalCache.set(cacheKey, result, namespace=CacheNamespace.FILER_EXTERNAL_API)
        return result


    async def get_track_data(opts: HelperParameters, validate=True): 
        isCached = True # assuming true from the start
        result = await opts.internal.internalCache.get(opts.internal.cacheKey.internal, namespace=opts.internal.cacheKey.namespace)

        if result is None:
            isCached = False
            
            summarize = opts.content == ResponseContent.SUMMARY
            countsOnly = opts.content == ResponseContent.COUNTS or summarize == True # if summarize is true, we only want counts
            
            # FIXME: getattr raises KeyError / ternary not working either -> related to Pydantic
            # tracks = None
            # if 'track' in opts.parameters:
            #     tracks = opts.parameters.track
            # else:
            #     tracks = opts.parameters._track
            
            tracks = get_attribute(opts.parameters, 'track', get_attribute(opts.parameters, '_track'))
            tracks = tracks.split(',') if isinstance(tracks, str) else tracks
            tracks = sorted(tracks) # best for caching
            
            assembly = get_attribute(opts.parameters, 'assembly')
            if validate or assembly is None: # for internal helper calls, don't always need to validate; already done
                assembly = await __validate_tracks(opts.internal.session, tracks)         
                
            cacheKey = f'/{FILERApiEndpoint.OVERLAPS}?countsOnly={countsOnly}&span={opts.parameters.span}&tracks=' 
            cacheKey = cacheKey.replace(':', '_')
            
            if countsOnly: # summarize & counts only do not need to be chunked
                result = await __get_track_data_task(tracks, assembly, opts.parameters.span, countsOnly, cacheKey, opts.internal)
            
                if summarize: # summarize doesn't need to be chunked b/c DB query
                    metadata: List[Track] = await get_track_metadata(opts, rawResponse=True)
                    result = __merge_track_lists([t.serialize(promoteObjs=True) for t in metadata], [t.serialize() for t in result])
                    result = sorted(result, key = lambda item: item['num_overlaps'], reverse=True)
                    # this step will be cached in __generate_response
                    
            else: # make parallel calls for large lists of tracks
                chunks = chunker(tracks, TRACKS_PER_API_REQUEST_LIMIT, returnIterator=True)
                tasks = [__get_track_data_task(c, assembly, opts.parameters.span, countsOnly, cacheKey, opts.internal) for c in chunks]
                result = await asyncio.gather(tasks)
                
        return await __generate_response(result, opts, isCached=isCached)


    async def get_track_metadata(opts: HelperParameters, rawResponse=False):
        isCached = True # assuming true from the start
        result = await opts.internal.internalCache.get(opts.internal.cacheKey.internal, namespace=opts.internal.cacheKey.namespace)
        if result is None:
            isCached = False
            
            # FIXME: get/getattr not working w/default -- Pydantic issue / also ternary not working
            tracks = None
            if 'track' in opts.parameters:
                tracks = opts.parameters.track
            else:
                tracks = opts.parameters._track
            tracks = tracks.split(',') if isinstance(tracks, str) else tracks
            
            result = await MetadataQueryService(opts.internal.session).get_track_metadata(tracks)
            
        if rawResponse:
            return result
        return await __generate_response(result, opts, isCached=isCached)


    async def search_track_metadata(self, opts: HelperParameters):
        isCached = True # assuming true from the start
        result = await opts.internal.internalCache.get(opts.internal.cacheKey.internal, namespace=opts.internal.cacheKey.namespace)
        
        if result is None:
            isCached = False
            if opts.pagination is not None and opts.content != ResponseContent.COUNTS:
                counts = await MetadataQueryService(opts.internal.session) \
                    .query_track_metadata(opts.parameters.assembly, 
                        opts.parameters.filter, opts.parameters.keyword, ResponseContent.COUNTS)
                self.__resultSize = counts['track_count']
                self.__page_metadata_query(opts.pagination.page)
                opts.pagination.total_num_records = self.__resultSize
                opts.pagination.total_num_pages = self.__totalNumPages

            result = await MetadataQueryService(opts.internal.session) \
                .query_track_metadata(opts.parameters.assembly, 
                    opts.parameters.filter, opts.parameters.keyword, opts.content, self.__limit, self.__offset)

        return await __generate_response(result, opts, isCached=isCached)


    async def search_track_data(opts: HelperParameters):
        result = await opts.internal.internalCache.get(opts.internal.cacheKey.internal, namespace=opts.internal.cacheKey.namespace)
        if result is not None: # just return the response
            return await __generate_response(result, opts, isCached=True)
        
        matchingTracks = await MetadataQueryService(opts.internal.session) \
            .query_track_metadata(opts.parameters.assembly,
                opts.parameters.filter, opts.parameters.keyword, 
                ResponseContent.IDS)
            
        # we want to cache the external FILER api call as well
        # to do so, we will add the tracks into the cache key b/c the tracks may not have 
        # been part of the original request (i.e., called from another helper)
        cacheKey = f'/{FILERApiEndpoint.INFORMATIVE_TRACKS}?genomeBuild={opts.parameters.assembly}&span={opts.parameters.span}' 
        cacheKey = cacheKey.replace(':','_')
        informativeTracks = await opts.internal.internalCache.get(cacheKey, namespace=CacheNamespace.FILER_EXTERNAL_API)
        if informativeTracks is None:
            # get tracks with data in the region
            informativeTracks = await ApiWrapperService() \
                .get_informative_tracks(opts.parameters.span, opts.parameters.assembly)
            # cache this response from the FILER Api
            await opts.internal.internalCache.set(cacheKey, informativeTracks, namespace=CacheNamespace.FILER_EXTERNAL_API)
        
        # filter for tracks that match the filter
        matchingTrackIds = matchingTracks 
        informativeTrackIds = [t['track_id'] for t in informativeTracks] # dict
        targetTrackIds = list(set(matchingTrackIds).intersection(informativeTrackIds))
        targetTracks = [t for t in informativeTracks if t['track_id'] in targetTrackIds]
        
        LOGGER.info("target tracks found")
        
        if opts.content == ResponseContent.FULL:
            pagedTrackIds, resultSize, numPages = __page_track_data_query(targetTracks, page=opts.pagination.page)
            opts.parameters._track = pagedTrackIds
            opts.pagination.total_num_records = resultSize
            opts.pagination.total_num_pages = numPages

        else:
            opts.parameters._track = targetTrackIds
            if opts.content == ResponseContent.IDS:
                return await __generate_response(targetTrackIds, opts)
            
        result = await get_track_data(opts, validate=False)
        return result

