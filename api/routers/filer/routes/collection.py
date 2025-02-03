from fastapi import APIRouter, Depends, Query
from typing import Annotated, Union

from api.common.enums import Assembly, ResponseContent
from api.common.exceptions import RESPONSES
from api.common.formatters import print_enum_values
from api.common.helpers import Parameters, ResponseConfiguration

from api.dependencies.parameters.location import assembly_param, span_param
from api.dependencies.parameters.optional import PaginationParameters, format_param, get_response_content, keyword_param, format_param, validate_response_content

from api.models.base_response_models import BaseResponseModel
from api.models.collection import CollectionResponse

from ..common.enums import METADATA_CONTENT_ENUM
from ..common.helpers import FILERRouteHelper
from ..common.services import MetadataQueryService
from ..dependencies.parameters import InternalRequestParameters, path_collection_name
from ..models.filer_track import FILERTrackBriefResponse, FILERTrackResponse

router = APIRouter(prefix="/collection", tags = ["Collections"], responses=RESPONSES)

@router.get("/", 
    response_model=CollectionResponse, 
    name="Get FILER Track Collections", 
    description="list available collections of related FILER tracks")
async def get_collections(format: str = Depends(format_param), internal: InternalRequestParameters = Depends())-> CollectionResponse:
    
    helper = FILERRouteHelper(
        internal,
        ResponseConfiguration(
            format=format,
            content=ResponseContent.FULL,
            model=CollectionResponse
        ), 
        Parameters()
    )
    
    result = await MetadataQueryService(internal.session).get_collections()
    return await helper.generate_response(result)


@router.get("/{collection}",
    response_model=Union[BaseResponseModel, FILERTrackBriefResponse, FILERTrackResponse],
    name="Get track metadata by collection", 
    description="retrieve full metadata for FILER track records associated with a collection")
async def get_collection_track_metadata(
    collection: str = Depends(path_collection_name),
    format: str = Depends(format_param), 
    content: str = Query(ResponseContent.FULL, description=f'response content; one of: {print_enum_values(METADATA_CONTENT_ENUM)}'),
    internal: InternalRequestParameters = Depends())-> CollectionResponse:
    
    rContent = validate_response_content(METADATA_CONTENT_ENUM, content)
    helper = FILERRouteHelper(
        internal,
        ResponseConfiguration(
            format=format,
            content=rContent,
            model=FILERTrackResponse if rContent == ResponseContent.FULL \
                else FILERTrackBriefResponse 
        ), 
        Parameters(collection=collection)
    )
    
    return await helper.get_collection_track_metadata()
