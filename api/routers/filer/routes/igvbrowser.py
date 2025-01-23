from fastapi import APIRouter, Depends, Query
from fastapi.exceptions import RequestValidationError
from typing import Union

from api.common.enums import ResponseContent
from api.common.exceptions import RESPONSES
from api.common.helpers import Parameters, ResponseConfiguration

from api.dependencies.parameters.filters import ExpressionType, FilterParameter
from api.dependencies.parameters.location import Assembly, assembly_param
from api.dependencies.parameters.optional import keyword_param
from api.models.base_response_models import BaseResponseModel
from api.models.igvbrowser import IGVBrowserTrackSelecterResponse, IGVBrowserTrackConfigResponse


from ..common.enums import METADATA_CONTENT_ENUM
from ..common.helpers import FILERRouteHelper
from ..common.constants import TRACK_SEARCH_FILTER_FIELD_MAP
from ..dependencies.parameters import InternalRequestParameters, query_track_id

router = APIRouter(prefix="/igvbrowser", responses=RESPONSES)

tags = ["NIAGADS Genome Browser Configuration"]

@router.get("/config", tags=tags, response_model=IGVBrowserTrackConfigResponse,
    name="Get IGV Genome Browser configuration for FILER tracks",
    description="retrieve NIAGADS Genome Browser track configuration for one or more FILER `track`(s) by ID, collection, or keyword search")
async def get_track_browser_config(
        track = Depends(query_track_id),
        assembly: Assembly = Depends(assembly_param), 
        collection: str = Query(default=None, description="retrieve specific track collection"),
        keyword: str = Depends(keyword_param),
        internal: InternalRequestParameters = Depends()
        
    ) -> IGVBrowserTrackConfigResponse:

    helper = FILERRouteHelper(
        internal,
        ResponseConfiguration(
            content=ResponseContent.SUMMARY,
            model=IGVBrowserTrackConfigResponse
        ),
        Parameters(track=track, assembly=assembly, collection=collection, keyword=keyword)
    )

    # TODO: collection & keyword?
    if keyword is not None:
        return await helper.search_track_metadata()
    elif collection is not None:
        pass
        # return await helper.get_track_collection()
    else:
        return await helper.get_track_metadata()
    

@router.get("/selector", tags=tags, response_model=IGVBrowserTrackSelecterResponse,
    name="Get Genome Browser track selector for FILER tracks",
    description="retrieve NIAGADS Genome Browser track selector table for one or more FILER `track`(s) by ID, collection, or keyword")
async def get_track_browser_config(
        track = Depends(query_track_id),
        assembly: Assembly = Depends(assembly_param), 
        collection: str = Query(default=None, description="retrieve specific track collection"),
        keyword: str = Depends(keyword_param),
        internal: InternalRequestParameters = Depends()
    ) -> IGVBrowserTrackSelecterResponse:

    helper = FILERRouteHelper(
        internal,
        ResponseConfiguration(
            content=ResponseContent.SUMMARY,
            model=IGVBrowserTrackSelecterResponse
        ),
        Parameters(track=track, assembly=assembly, collection=collection, keyword=keyword)
    )

    # TODO: collection & keyword?
    if keyword is not None:
        return await helper.search_track_metadata()
    elif collection is not None:
        pass
        # return await helper.get_track_collection()
    else:
        return await helper.get_track_metadata()
    

