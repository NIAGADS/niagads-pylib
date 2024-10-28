from typing import Any, List
from fastapi import status
from fastapi.exceptions import RequestValidationError
from fastapi.responses import RedirectResponse
from sqlalchemy.ext.asyncio import AsyncSession
from collections import ChainMap, OrderedDict
from itertools import groupby
from operator import itemgetter


from api.common.enums import ResponseContent
from api.common.helpers import HelperParameters as __BaseHelperParameters, Parameters
from api.dependencies.parameters.optional import ResponseFormat
from api.response_models.base_models import BaseResponseModel, RequestDataModel, PaginationDataModel
from api.routers.filer.models.track_response_model import FILERTrackBrief

from .services import MetadataQueryService, ApiWrapperService
from ..dependencies import InternalRequestParameters
from ..models.track_metadata_cache import Track

DEFAULT_PAGE_SIZE = 5000
class HelperParameters(__BaseHelperParameters):
    internal: InternalRequestParameters


def __merge_track_lists(trackList1, trackList2):
    matched = groupby(sorted(trackList1 + trackList2, key=itemgetter('track_id')), itemgetter('track_id'))
    combinedLists = [dict(ChainMap(*g)) for k, g in matched]
    return combinedLists
    

async def __generate_cache_key(requestData: RequestDataModel, model: BaseResponseModel, suffix: str=None):
    if model.is_paged():
        return requestData.request_id + (f'_{suffix}' if suffix is not None else '')
    else: 
        raise NotImplementedError('Need to use auto-generated cache key based on endpoint and parameters')


def __page_track_data_query(trackSummary: dict, page: int, pageSize: int = DEFAULT_PAGE_SIZE):
    expectedResultSize = sum([ t['num_overlaps'] for t in trackSummary])
    if expectedResultSize < pageSize and page == 1:
        return [t['track_id'] for t in trackSummary], None
    
    # TODO; page result, calc offset based on current page, etc.
    pagedTracks = []
    count = 0
    sortedTrackSummary = sorted(trackSummary, key = lambda item: item['num_overlaps'], reverse=True)
    for track in trackSummary:
        if count + track['num_overlaps'] <= pageSize:
            pagedTracks.append(track['track_id'])
            count += track['num_overlaps']
            
    message = 'Paging not yet implemented. Result has been truncated to 5000 records. To determine the most informative tracks in the search region, please run with `content=summary`'
    return pagedTracks, message
    

# TODO:
# paged response; by requestId, others by auto-generated based on request and params?
# cache -> expected response as requestID_response, 
# cache requestData as requestID_request so that original URL and params are passed   

async def __validate_tracks(session: AsyncSession, tracks: List[str]):
    """ by setting validate=True, the service runs .validate_tracks before validating the genome build"""
    assembly = await MetadataQueryService(session).get_genome_build(tracks, validate=True)
    if isinstance(assembly, dict):
        raise RequestValidationError(f'Tracks map to multiple assemblies; please query GRCh37 and GRCh38 data independently')
    

def __generate_response(result: Any, opts:HelperParameters):
    rowModel = opts.model.row_model(name=True)
    requestId = opts.internal.requestData.request_id
    isPaged = opts.model.is_paged()
    if isPaged:
        numRecords = len(result)
        pagination = PaginationDataModel(page=1, total_num_pages=1, paged_num_records=numRecords, total_num_records=numRecords)

    match opts.format:
        case ResponseFormat.TABLE:
            redirectUrl = f'/view/table/{rowModel}?forwardingRequestId={requestId}'
            return RedirectResponse(url=redirectUrl, status_code=status.HTTP_303_SEE_OTHER)
        case _:
            if isPaged:
                return opts.model(request=opts.internal.requestData, pagination=pagination, response=result)
            return opts.model(request=opts.internal.requestData, response=result)


async def get_track_data(opts: HelperParameters, validate=True): 
    summarize = opts.content == ResponseContent.SUMMARY
    countsOnly = opts.content == ResponseContent.COUNTS or summarize == True # if summarize is true, we only want counts
    tracks = opts.parameters.track.split(',') \
        if isinstance(opts.parameters.track, str) \
            else opts.parameters.track
    
    if validate: # for internal helper calls, don't always need to validate; already done
        await __validate_tracks(opts.internal.session, tracks)  
        
    result = await ApiWrapperService().get_track_hits(tracks, opts.parameters.span, countsOnly=countsOnly)

    if summarize:
        metadata: List[Track] = await get_track_metadata(opts, rawResponse=True)
        result = __merge_track_lists([t.serialize(promoteObjs=True) for t in metadata], [t.serialize() for t in result])
        result = sorted(result, key = lambda item: item['num_overlaps'], reverse=True)
        
    return __generate_response(result, opts)


async def get_track_metadata(opts: HelperParameters, rawResponse=False):
    tracks = opts.parameters.track.split(',') \
        if isinstance(opts.parameters.track, str) \
            else opts.parameters.track  
    result = await MetadataQueryService(opts.internal.session).get_track_metadata(tracks)
    if rawResponse:
        return result
    return __generate_response(result, opts)


async def search_track_metadata(opts: HelperParameters):
    result =  await MetadataQueryService(opts.internal.session) \
        .query_track_metadata(opts.parameters.assembly, 
            opts.parameters.filter, opts.parameters.keyword, opts.content)
        
    return __generate_response(result, opts)


async def search_track_data(opts: HelperParameters):
    matchingTracks = await MetadataQueryService(opts.internal.session) \
        .query_track_metadata(opts.parameters.assembly,
            opts.parameters.filter, opts.parameters.keyword, 
            ResponseContent.IDS)
    
    # get tracks with data in the region
    informativeTracks = await ApiWrapperService() \
        .get_informative_tracks(opts.parameters.span, opts.parameters.assembly)
    
    # filter for tracks that match the filter
    matchingTrackIds = matchingTracks 
    informativeTrackIds = [t['track_id'] for t in informativeTracks] # dict
    targetTrackIds = list(set(matchingTrackIds).intersection(informativeTrackIds))
    targetTracks = [t for t in informativeTracks if t['track_id'] in targetTrackIds]
    
    if opts.content == ResponseContent.FULL:
        pagedTrackIds, message = __page_track_data_query(targetTracks, page=1)
        
        if message is not None:
            opts.internal.requestData.message = message
        opts.parameters.track = pagedTrackIds
    else:
        opts.parameters.track = targetTrackIds
        
    return await get_track_data(opts, validate=False)
