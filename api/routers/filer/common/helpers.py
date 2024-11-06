from typing import List
from fastapi.exceptions import RequestValidationError
from sqlalchemy.ext.asyncio import AsyncSession
from collections import ChainMap
from itertools import groupby
from operator import itemgetter

from niagads.utils.list import cumulative_sum, chunker

from api.common.enums import ResponseContent, CacheNamespace
from api.common.helpers import HelperParameters as __BaseHelperParameters, generate_response as __generate_response
from api.dependencies.parameters.optional import PaginationParameters

from .services import MetadataQueryService, ApiWrapperService
from ..dependencies import InternalRequestParameters
from ..models.track_metadata_cache import Track

TRACKS_PER_REQUEST_LIMIT = 200
DEFAULT_PAGE_SIZE = 5000
MAX_NUM_PAGES = 500
class HelperParameters(__BaseHelperParameters):
    internal: InternalRequestParameters


def __merge_track_lists(trackList1, trackList2):
    matched = groupby(sorted(trackList1 + trackList2, key=itemgetter('track_id')), itemgetter('track_id'))
    combinedLists = [dict(ChainMap(*g)) for k, g in matched]
    return combinedLists


def __page_metadata_query(expectedResultSize, page: int, pageSize:int = DEFAULT_PAGE_SIZE):
    """ XXX: not satisfied w/this solution; revisit
    FIXME: template out the common elements w/__page_track_data_query
    Returns
        OFFSET, LIMIT, expectedResultSize, expectedNumPages
    """
    if expectedResultSize < pageSize and page == 1:
        return None, None, 1
    
    expectedNumPages = next((p for p in range(1,500) if (p - 1) * pageSize > expectedResultSize)) - 1
    if page > expectedNumPages:
        raise RequestValidationError(f'Request `page` {page} does not exist; this query generates a maximum of {expectedNumPages} pages')
    
    return pageSize, (page - 1) * pageSize, expectedNumPages

    
def __page_track_data_query(trackSummary: dict, page: int, pageSize: int = DEFAULT_PAGE_SIZE):
    sortedTrackSummary = sorted(trackSummary, key = lambda item: item['num_overlaps'], reverse=True)
    cumulativeSum = cumulative_sum([t['num_overlaps'] for t in sortedTrackSummary])
    expectedResultSize = cumulativeSum[-1]
    if expectedResultSize < pageSize and page == 1:
        return [t['track_id'] for t in trackSummary], expectedResultSize, 1
    
    minRecordRowIndex = (page - 1) * pageSize
    maxRecordRowIndex = minRecordRowIndex + pageSize
    if maxRecordRowIndex > expectedResultSize:
        maxRecordRowIndex = expectedResultSize
    
    expectedNumPages = next((p for p in range(1,500) if (p - 1) * pageSize > expectedResultSize)) - 1
    if page > expectedNumPages:
        raise RequestValidationError(f'Request `page` {page} does not exist; this query generates a maximum of {expectedNumPages} pages')
    # () returns an iterator instead of a list; i.e. []
    pageStartIndex = next((index for index, counts in enumerate(cumulativeSum) if counts >= minRecordRowIndex))
    pageEndIndex = len(cumulativeSum) - 1 if maxRecordRowIndex == expectedResultSize \
        else next((index for index, counts in enumerate(cumulativeSum) if counts >= maxRecordRowIndex)) - 1
    pagedTracks = [t['track_id'] for t in sortedTrackSummary[pageStartIndex:pageEndIndex]]
    
    return pagedTracks, expectedResultSize, expectedNumPages
    

# TODO:
# paged response; by requestId, others by auto-generated based on request and params?
# cache -> expected response as requestID_response, 
# cache requestData as requestID_request so that original URL and params are passed   

async def __validate_tracks(session: AsyncSession, tracks: List[str]):
    """ by setting validate=True, the service runs .validate_tracks before validating the genome build"""
    assembly = await MetadataQueryService(session).get_genome_build(tracks, validate=True)
    if isinstance(assembly, dict):
        raise RequestValidationError(f'Tracks map to multiple assemblies; please query GRCh37 and GRCh38 data independently')
    

async def get_track_data(opts: HelperParameters, validate=True): 
    isCached = True # assuming true from the start
    result = await opts.internal.internalCache.get(opts.internal.cacheKey.internal, namespace=opts.internal.cacheKey.namespace)

    if result is None:
        isCached = False
        
        summarize = opts.content == ResponseContent.SUMMARY
        countsOnly = opts.content == ResponseContent.COUNTS or summarize == True # if summarize is true, we only want counts
        tracks = opts.parameters.track.split(',') \
            if isinstance(opts.parameters.track, str) \
                else opts.parameters.track
        tracks = sorted(tracks) # best for caching
        
        # do we need to make multiple calls? i.e. if the # of tracks is too many (exceeds URL length)
        chunks = chunker(tracks, TRACKS_PER_REQUEST_LIMIT, returnIterator=True)
        result = []
        for c in chunks:
            # we want to cache the external FILER api call as well
            # to do so, we will add the tracks into the cache key b/c the tracks may not have 
            # been part of the original request (i.e., called from another helper)
            cacheTrackCheck = ','.join(c)
            cacheKey = f'/data?countsOnly={countsOnly}&span={opts.parameters.span}&tracks={cacheTrackCheck}' 
            cacheKey = cacheKey.replace(':', '_')
            partialResult = await opts.internal.internalCache.get(cacheKey, namespace=CacheNamespace.FILER_EXTERNAL_API)
            if partialResult is None: 
                if validate: # for internal helper calls, don't always need to validate; already done
                    await __validate_tracks(opts.internal.session, c)         
                partialResult = await ApiWrapperService().get_track_hits(c, opts.parameters.span, countsOnly=countsOnly)
                # cache this response from the FILER Api
                await opts.internal.internalCache.set(cacheKey, partialResult, namespace=CacheNamespace.FILER_EXTERNAL_API)
        
            result = result + partialResult
                
        if summarize: # summarize doesn't need to be chunked b/c DB query
            metadata: List[Track] = await get_track_metadata(opts, rawResponse=True)
            result = __merge_track_lists([t.serialize(promoteObjs=True) for t in metadata], [t.serialize() for t in result])
            result = sorted(result, key = lambda item: item['num_overlaps'], reverse=True)
            # this step will be cached in __generate_response
        
    return await __generate_response(result, opts, isCached=isCached)


async def get_track_metadata(opts: HelperParameters, rawResponse=False):
    isCached = True # assuming true from the start
    result = await opts.internal.internalCache.get(opts.internal.cacheKey.internal, namespace=opts.internal.cacheKey.namespace)
    if result is None:
        isCached = False
                
        tracks = opts.parameters.track.split(',') \
            if isinstance(opts.parameters.track, str) \
                else opts.parameters.track  
        
        result = await MetadataQueryService(opts.internal.session).get_track_metadata(tracks)
        
    if rawResponse:
        return result
    return await __generate_response(result, opts, isCached=isCached)


async def search_track_metadata(opts: HelperParameters):
    isCached = True # assuming true from the start
    result = await opts.internal.internalCache.get(opts.internal.cacheKey.internal, namespace=opts.internal.cacheKey.namespace)
    
    if result is None:
        isCached = False
        limit = None
        offset = None
        if opts.pagination is not None and opts.content != ResponseContent.COUNTS:
            counts =  await MetadataQueryService(opts.internal.session) \
                .query_track_metadata(opts.parameters.assembly, 
                    opts.parameters.filter, opts.parameters.keyword, ResponseContent.COUNTS)
            limit, offset, numPages = __page_metadata_query(counts['track_count'], opts.pagination.page)
            opts.parameters.expected_result_size = counts['track_count']
            opts.parameters.total_page_count = numPages

        result =  await MetadataQueryService(opts.internal.session) \
            .query_track_metadata(opts.parameters.assembly, 
                opts.parameters.filter, opts.parameters.keyword, opts.content, limit, offset)

        
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
    cacheKey = f'/data_summary?assembly={opts.parameters.assembly}&span={opts.parameters.span}' 
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
    
    if opts.content == ResponseContent.FULL:
        pagedTrackIds, resultSize, numPages = __page_track_data_query(targetTracks, page=opts.pagination.page)
        opts.parameters.track = pagedTrackIds
        opts.parameters.expected_result_size = resultSize
        opts.parameters.total_page_count = numPages
    else:
        opts.parameters.track = targetTrackIds
        if opts.content == ResponseContent.IDS:
            return await __generate_response(targetTrackIds, opts)
        
    return await get_track_data(opts, validate=False)
