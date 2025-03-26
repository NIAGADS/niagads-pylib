from fastapi import APIRouter, Depends, Query
from typing import Union

from api.common.enums.response_properties import ResponseContent, ResponseFormat, ResponseView
from api.common.exceptions import RESPONSES
from api.common.helpers import Parameters, ResponseConfiguration

from api.dependencies.parameters.identifiers import path_collection_name
from api.dependencies.parameters.optional import page_param

from api.models.base_response_models import BaseResponseModel
from api.models.collection import CollectionResponse
from api.models.view_models import TableViewResponse

from api.routes.genomics.common.helpers import GenomicsRouteHelper
from api.routes.genomics.dependencies.parameters import InternalRequestParameters
from api.routes.genomics.models.genomics_track import GenomicsTrackResponse, GenomicsTrackSummaryResponse
from api.routes.genomics.queries.track_metadata import CollectionQuery, CollectionTrackMetadataQuery

router = APIRouter(prefix="/collection", tags = ["Collections"], responses=RESPONSES)

@router.get("/", 
    response_model=CollectionResponse, 
    name="Get GenomicsDB Track Collections", 
    description="list available collections of related GenomicsDB tracks")

async def get_collections(
    format: str = Query(ResponseFormat.JSON, description=ResponseFormat.generic(description=True)), 
    internal: InternalRequestParameters = Depends()
)-> CollectionResponse:
    

    helper = GenomicsRouteHelper(
        internal,
        ResponseConfiguration(
            format=ResponseFormat.generic().validate(format, 'format', ResponseFormat),
            content=ResponseContent.FULL,
            model=CollectionResponse
        ), 
        Parameters(),
        query=CollectionQuery
    )

    
    return await helper.get_query_response()


@router.get("/{collection}",
    response_model=Union[BaseResponseModel, GenomicsTrackSummaryResponse, GenomicsTrackResponse, TableViewResponse],
    name="Get track metadata by collection", 
    description="retrieve full metadata for FILER track records associated with a collection")

async def get_collection_track_metadata(
    collection: str = Depends(path_collection_name),
    page: int=Depends(page_param),
    content: str = Query(ResponseContent.FULL, description=ResponseContent.get_description(True)),
    format: str = Query(ResponseFormat.JSON, description=ResponseFormat.generic(description=True)),
    view: str =  Query(ResponseView.DEFAULT, description=ResponseView.table(description=True)),
    internal: InternalRequestParameters = Depends()
)-> Union[BaseResponseModel, GenomicsTrackSummaryResponse, GenomicsTrackResponse,TableViewResponse]:
    
    rContent = ResponseContent.validate(content, 'content', ResponseContent)
    helper = GenomicsRouteHelper(
        internal,
        ResponseConfiguration(
            format=ResponseFormat.generic().validate(format, 'format', ResponseFormat),
            content=rContent,
            view=ResponseView.table().validate(view, 'view', ResponseView), 
            model=GenomicsTrackResponse if rContent == ResponseContent.FULL \
                else GenomicsTrackSummaryResponse if rContent == ResponseContent.SUMMARY \
                    else BaseResponseModel
        ), 
        Parameters(collection=collection, page=page),
        query=CollectionTrackMetadataQuery
    )
    
    return await helper.get_query_response()
