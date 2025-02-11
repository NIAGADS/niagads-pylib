from fastapi import APIRouter, Depends, Query
from typing import Union

from api.common.enums import Assembly, ResponseContent, ResponseFormat, ResponseView
from api.common.exceptions import RESPONSES
from api.common.helpers import Parameters, ResponseConfiguration

from api.dependencies.parameters.location import assembly_param, span_param
from api.dependencies.parameters.optional import keyword_param, page_param

from api.models.base_response_models import PagedResponseModel
from api.models.view_models import TableViewResponseModel

from ..common.helpers import FILERRouteHelper
from ..dependencies.parameters import METADATA_FILTER_PARAM, InternalRequestParameters, required_query_track_id
from ..models.filer_track import FILERTrackBriefResponse
from ..models.bed_features import BEDResponse

router = APIRouter(prefix="/data", responses=RESPONSES)

tags = ["Track Data by ID"]
# get_track_data_content_enum = get_response_content(exclude=[ResponseContent.IDS, ResponseContent.URLS])

@router.get("/", tags=tags,
    name="Get data from multiple tracks by ID", 
    response_model=Union[BEDResponse, PagedResponseModel, FILERTrackBriefResponse, TableViewResponseModel],
    description="retrieve data from one or more FILER tracks in the specified region")

async def get_track_data(
    track: str = Depends(required_query_track_id),
    span: str = Depends(span_param),
    page: int = Depends(page_param),
    content: str = Query(ResponseContent.FULL, description=ResponseContent.data(description=True)),
    format: str = Query(ResponseFormat.JSON, description=ResponseFormat.functional_genomics(description=True)),
    view: str = Query(ResponseView.DEFAULT, description=ResponseView.get_description()),
    internal: InternalRequestParameters = Depends()
) -> Union[BEDResponse, PagedResponseModel, FILERTrackBriefResponse, TableViewResponseModel]:
    
    rContent = ResponseContent.data().validate(content, 'content', ResponseContent)
    helper = FILERRouteHelper(
        internal,
        ResponseConfiguration(
            format=ResponseFormat.functional_genomics().validate(format, 'format', ResponseFormat),
            content=rContent,
            view=ResponseView.validate(view, 'view', ResponseView),
            model=BEDResponse if rContent == ResponseContent.FULL \
                else FILERTrackBriefResponse if rContent == ResponseContent.SUMMARY \
                    else PagedResponseModel
        ), 
        Parameters(track=track, span=span, page=page)
    )
    
    return await helper.get_track_data()


tags = ['Record(s) by Text Search'] + ['Track Data by Text Search'] + ['Track Data by Genomic Region']

@router.get("/search", tags=tags, 
    response_model=Union[PagedResponseModel, FILERTrackBriefResponse, BEDResponse, TableViewResponseModel],
    name="Get data from multiple tracks by Search", 
    description="find functional genomics tracks with data in specified region; qualify using category filters or by a keyword search against all text fields in the track metadata")

async def get_track_data_by_metadata_search(
    assembly: Assembly = Depends(assembly_param), 
    span: str = Depends(span_param),
    filter = Depends(METADATA_FILTER_PARAM), 
    keyword: str = Depends(keyword_param),
    page:int=Depends(page_param),
    content: str = Query(ResponseContent.FULL, description=ResponseContent.data(description=True)),
    format: str = Query(ResponseFormat.JSON, description=ResponseFormat.functional_genomics(description=True)),
    view: str = Query(ResponseView.DEFAULT, description=ResponseView.get_description()),
    internal: InternalRequestParameters = Depends(),
) -> Union[PagedResponseModel, FILERTrackBriefResponse, BEDResponse, TableViewResponseModel]:
    
    rContent = ResponseContent.data().validate(content, 'content', ResponseContent)
    helper = FILERRouteHelper(
        internal,
        ResponseConfiguration(
            format=ResponseFormat.functional_genomics().validate(format, 'format', ResponseFormat),
            content=rContent,
            view=ResponseView.validate(view, 'view', ResponseView),
            model=BEDResponse if rContent == ResponseContent.FULL \
                else FILERTrackBriefResponse if rContent == ResponseContent.SUMMARY \
                    else PagedResponseModel
        ),
        Parameters(assembly=assembly, filter=filter, keyword=keyword, span=span, page=page)
    )
    
    return await helper.search_track_data()