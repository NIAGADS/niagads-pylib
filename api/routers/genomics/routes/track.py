from fastapi import APIRouter, Depends, Query
from typing import Union

from api.common.enums.response_properties import ResponseContent, ResponseFormat, ResponseView
from api.common.exceptions import RESPONSES
from api.common.helpers import Parameters, ResponseConfiguration

from api.dependencies.parameters.location import span_param
from api.dependencies.parameters.optional import page_param
from api.dependencies.parameters.path import path_track_id
from api.models.base_response_models import PagedResponseModel, BaseResponseModel
from api.models.view_models import TableViewResponseModel
from api.routers.genomics.common.helpers import GenomicsRouteHelper
from api.routers.genomics.dependencies.parameters import InternalRequestParameters
from api.routers.genomics.models.genomics_track import GenomicsTrackResponse, GenomicsTrackSummaryResponse
from api.routers.genomics.queries.track_metadata import TrackMetadataQuery


router = APIRouter(prefix="/track", responses=RESPONSES)

tags = ["Record by ID", "Track Metadata by ID"]
@router.get("/{track}", tags=tags,
    response_model=Union[GenomicsTrackSummaryResponse, GenomicsTrackResponse , BaseResponseModel],
    name="Get track metadata",
    description="retrieve track metadata for the FILER record identified by the `track` specified in the path; use `content=summary` for a brief response")

async def get_track_metadata(
    track = Depends(path_track_id),
    content: str = Query(ResponseContent.SUMMARY, description=ResponseContent.descriptive(description=True)),
    format: str = Query(ResponseFormat.JSON, description=ResponseFormat.generic(description=True)),
    internal: InternalRequestParameters = Depends()
) -> Union[GenomicsTrackSummaryResponse, GenomicsTrackResponse, BaseResponseModel]:
    
    rContent = ResponseContent.descriptive().validate(content, 'content', ResponseContent)
    rFormat = ResponseFormat.generic().validate(format, 'format', ResponseFormat)
    helper = GenomicsRouteHelper(
        internal,
        ResponseConfiguration(
            content=rContent,
            format=rFormat,
            model = GenomicsTrackResponse if rContent == ResponseContent.FULL \
                else GenomicsTrackSummaryResponse
        ),
        Parameters(track=track),
        idParameter='track',
        query=TrackMetadataQuery
    )
    
    return await helper.get_query_response()


"""
tags = ["Record by ID", "Track Data by ID"]

@router.get("/{track}/data", tags=tags,
    name="Get track data",
    response_model=Union[BEDResponse, FILERTrackSummaryResponse, TableViewResponseModel, PagedResponseModel],
    description="retrieve functional genomics track data from FILER in the specified region; specify `content=counts` to just retrieve a count of the number of hits in the specified region")

async def get_track_data(
    track = Depends(path_track_id),
    span:str=Depends(span_param),
    page:int=Depends(page_param),
    content: str = Query(ResponseContent.FULL, description=ResponseContent.data(description=True)),
    format: str = Query(ResponseFormat.JSON, description=ResponseFormat.functional_genomics(description=True)),
    view: str = Query(ResponseView.DEFAULT, description=ResponseView.get_description()),
    internal: InternalRequestParameters = Depends()
) -> Union[BEDResponse, FILERTrackSummaryResponse, TableViewResponseModel, PagedResponseModel]:
    
    rContent = ResponseContent.data().validate(content, 'content', ResponseContent)
    helper = FILERRouteHelper(
        internal,
        ResponseConfiguration(
            content=rContent,
            format=ResponseFormat.functional_genomics().validate(format, 'format', ResponseFormat),
            view=ResponseView.validate(view, 'view', ResponseView),
            model=BEDResponse if rContent == ResponseContent.FULL \
                else FILERTrackSummaryResponse if rContent == ResponseContent.SUMMARY \
                else PagedResponseModel
        ),
        Parameters(track=track, span=span, page=page)
    )

    return await helper.get_track_data()


"""