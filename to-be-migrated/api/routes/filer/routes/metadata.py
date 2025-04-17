from fastapi import APIRouter, Depends, Query
from fastapi.exceptions import RequestValidationError
from typing import Union

from api.common.enums.genome import Assembly
from api.common.enums.response_properties import ResponseContent, ResponseFormat, ResponseView
from api.common.exceptions import RESPONSES
from api.common.helpers import Parameters, ResponseConfiguration

from api.dependencies.parameters.features import assembly_param
from api.dependencies.parameters.optional import page_param, keyword_param

from api.models.base_response_models import PagedResponseModel, ResponseModel
from api.models.view_models import TableViewResponse

from api.routes.filer.common.helpers import FILERRouteHelper
from api.routes.filer.models.filer_track import FILERTrackSummaryResponse, FILERTrackResponse
from api.routes.filer.dependencies.parameters import METADATA_FILTER_PARAM, InternalRequestParameters, required_query_track_id

router = APIRouter(prefix="/metadata", responses=RESPONSES)

tags = ["Track Metadata by ID"]

@router.get("/", tags=tags, 
    response_model=Union[FILERTrackResponse, FILERTrackSummaryResponse, TableViewResponse, ResponseModel],
    name="Get metadata for multiple tracks",
    description="retrieve full metadata for one or more FILER track records")

async def get_track_metadata(
    track: str = Depends(required_query_track_id),
    content: str = Query(ResponseContent.FULL, description=ResponseContent.descriptive(inclUrls=True, description=True)),
    format: str = Query(ResponseFormat.JSON, description=ResponseFormat.generic(description=True)),
    view: str =  Query(ResponseView.DEFAULT, description=ResponseView.table(description=True)),
    internal: InternalRequestParameters = Depends()
) -> Union[FILERTrackSummaryResponse, FILERTrackResponse, TableViewResponse, ResponseModel]:
    
    rContent = ResponseContent.descriptive(inclUrls=True).validate(content, 'content', ResponseContent)
    helper = FILERRouteHelper(
        internal,
        ResponseConfiguration(
            format=ResponseFormat.generic().validate(format, 'format', ResponseFormat),
            view=ResponseView.table().validate(view, 'view', ResponseView),
            content=rContent,
            model=FILERTrackResponse if rContent == ResponseContent.FULL \
                else FILERTrackSummaryResponse if rContent == ResponseContent.SUMMARY \
                    else ResponseModel
        ), 
        Parameters(track=track)
    )
    return await helper.get_track_metadata()


tags = ['Record(s) by Text Search'] + ['Track Metadata by Text Search']

@router.get("/search", tags=tags, 
    response_model=Union[PagedResponseModel, FILERTrackSummaryResponse, FILERTrackResponse, TableViewResponse],
    name="Search for tracks", 
    description="find functional genomics tracks using category filters or by a keyword search against all text fields in the track metadata")

async def search_track_metadata(
    filter = Depends(METADATA_FILTER_PARAM), 
    keyword: str = Depends(keyword_param),
    assembly: Assembly = Depends(assembly_param), 
    page: int = Depends(page_param),
    content: str = Query(ResponseContent.FULL, description=ResponseContent.get_description(True)),
    format: str = Query(ResponseFormat.JSON, description=ResponseFormat.generic(description=True)),
    view: str =  Query(ResponseView.DEFAULT, description=ResponseView.table(description=True)),
    internal: InternalRequestParameters = Depends(),
) -> Union[PagedResponseModel, FILERTrackSummaryResponse, FILERTrackResponse, TableViewResponse]:
    
    if filter is None and keyword is None:
        raise RequestValidationError('must specify either a `filter` and/or a `keyword` to search')
    
    rContent = ResponseContent.validate(content, 'content', ResponseContent)
    helper = FILERRouteHelper(
        internal,
        ResponseConfiguration(
            format=ResponseFormat.generic().validate(format, 'format', ResponseFormat),
            content=rContent,
            view=ResponseView.table().validate(view, 'view', ResponseView), 
            model=FILERTrackResponse if rContent == ResponseContent.FULL \
                else FILERTrackSummaryResponse if rContent == ResponseContent.SUMMARY \
                    else PagedResponseModel
        ),
        Parameters(
            page=page,
            assembly=assembly,
            filter=filter,
            keyword=keyword)
    )
    
    return await helper.search_track_metadata()

