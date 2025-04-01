from typing import List, Union
from fastapi import APIRouter, Depends, Query
from fastapi.exceptions import RequestValidationError

from api.common.enums.genome import Assembly
from api.common.enums.response_properties import ResponseContent, ResponseFormat, ResponseView
from api.common.exceptions import RESPONSES
from api.common.helpers import Parameters, ResponseConfiguration

from api.dependencies.parameters.identifiers import query_collection_name
from api.dependencies.parameters.features import assembly_param, chromosome_param
from api.models.base_response_models import BaseResponseModel
from api.models.igvbrowser import IGVBrowserTrackConfig, IGVBrowserTrackSelectorResponse, IGVBrowserTrackConfigResponse
from api.models.view_models import TableViewModel

from api.routes.filer.common.helpers import FILERRouteHelper
from api.routes.filer.dependencies.parameters import InternalRequestParameters, optional_query_track_id, required_query_track_id
from api.routes.filer.models.filer_track import FILERTrackResponse, FILERTrackSummaryResponse

router = APIRouter(prefix="/service", responses=RESPONSES)

tags = ["NIAGADS Genome Browser"]

@router.get("/igvbrowser/config", tags=tags, response_model=List[IGVBrowserTrackConfig],
    name="Get IGV Genome Browser for FILER tracks",
    description="retrieve NIAGADS Genome Browser track configuration for one or more FILER `track`(s) by ID or collection")
    # , or keyword search")
async def get_track_browser_config(
        track = Depends(optional_query_track_id),
        assembly: Assembly = Depends(assembly_param), 
        collection: str = Depends(query_collection_name),
        # keyword: str = Depends(keyword_param),
        internal: InternalRequestParameters = Depends()
        
    ) -> List[IGVBrowserTrackConfig]:

    helper = FILERRouteHelper(
        internal,
        ResponseConfiguration(
            content=ResponseContent.FULL,
            model=IGVBrowserTrackConfigResponse
        ),
        Parameters(track=track, assembly=assembly, collection=collection) #, keyword=keyword)
    )

    setParamCount = sum(x is not None for x in [collection, track]) # [collection, keyword, track])
    if setParamCount == 0 or setParamCount > 1:
        # FIXME: allow combinations
        raise RequestValidationError('please provide a value for exactly one of `collection`  or `track`')


    if collection is not None:
        result = await helper.get_collection_track_metadata()
    #elif keyword is not None:
    #    result = await helper.search_track_metadata()
    else:
        result = await helper.get_track_metadata()
        
    return result.response
    

@router.get("/igvbrowser/selector", tags=tags, response_model=TableViewModel,
    name="Get Genome Browser track selector for FILER tracks",
    description="retrieve NIAGADS Genome Browser track selector table for one or more FILER `track`(s) by ID or collection")
    #, or keyword")
async def get_track_browser_config(
        track = Depends(optional_query_track_id),
        assembly: Assembly = Depends(assembly_param), 
        collection: str = Depends(query_collection_name),
        # keyword: str = Depends(keyword_param),
        internal: InternalRequestParameters = Depends()
    ) -> TableViewModel:

    helper = FILERRouteHelper(
        internal,
        ResponseConfiguration(
            content=ResponseContent.FULL,
            model=IGVBrowserTrackSelectorResponse
        ),
        Parameters(track=track, assembly=assembly, collection=collection) #  keyword=keyword)
    )
    
    setParamCount = sum(x is not None for x in [collection, track]) #[collection, keyword, track])
    if setParamCount == 0 or setParamCount > 1:
        # FIXME: allow combinations
        raise RequestValidationError('please provide a value for exactly one of `collection` or `track`')


    if collection is not None:
        result = await helper.get_collection_track_metadata()
    # elif keyword is not None:
    #     result = await helper.search_track_metadata()
    else:
        result = await helper.get_track_metadata()
    
    return result.response


tags = ["Lookups"]

@router.get("/lookup/shard", tags=tags, 
    response_model=Union[FILERTrackResponse, FILERTrackSummaryResponse, BaseResponseModel],
    name="Get metadata shard metadata",
    description="Some tracks are sharded by chromosome.  Use this query to find a shard-specific track given a chromosome and related track identifier.")

async def get_shard(
    track: str = Depends(required_query_track_id),
    chr: str = Depends(chromosome_param),
    content: str = Query(ResponseContent.FULL, description=ResponseContent.descriptive(inclUrls=True, description=True)),
    format: str = Query(ResponseFormat.JSON, description=ResponseFormat.generic(description=True)),
    internal: InternalRequestParameters = Depends()
) -> Union[FILERTrackSummaryResponse, FILERTrackResponse, BaseResponseModel]:
    
    rContent = ResponseContent.descriptive(inclUrls=True).validate(content, 'content', ResponseContent)
    helper = FILERRouteHelper(
        internal,
        ResponseConfiguration(
            format=ResponseFormat.generic().validate(format, 'format', ResponseFormat),
            content=rContent,
            model=FILERTrackResponse if rContent == ResponseContent.FULL \
                else FILERTrackSummaryResponse if rContent == ResponseContent.SUMMARY \
                    else BaseResponseModel
        ), 
        Parameters(track=track, chromosome=chr)
    )
    
    return await helper.get_shard()