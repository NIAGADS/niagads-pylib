from typing import List
from fastapi import APIRouter, Depends
from fastapi.exceptions import RequestValidationError

from api.common.enums import ResponseContent
from api.common.exceptions import RESPONSES
from api.common.helpers import Parameters, ResponseConfiguration

from api.dependencies.parameters.location import Assembly, assembly_param
from api.dependencies.parameters.optional import keyword_param
from api.models.igvbrowser import IGVBrowserTrackConfig, IGVBrowserTrackSelectorResponse, IGVBrowserTrackConfigResponse
from api.models.view_models import TableViewModel

from ..common.helpers import FILERRouteHelper
from ..dependencies.parameters import InternalRequestParameters, optional_query_track_id, query_collection_name

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

