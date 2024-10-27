from fastapi import APIRouter, Depends, Query
from fastapi.exceptions import RequestValidationError
from typing import Annotated, Optional, Union

from api.common.exceptions import RESPONSES
from api.dependencies.parameters.filters import ExpressionType, FilterParameter
from api.dependencies.parameters.location import Assembly, assembly_param
from api.dependencies.parameters.optional import PaginationParameters, counts_only_param, format_param, ids_only_param, keyword_param
from api.response_models import GenomeBrowserConfigResponse, GenomeBrowserExtendedConfigResponse
from api.common.helpers import Parameters
from api.response_models.base_models import BaseResponseModel

from ..common.helpers import HelperParameters, get_track_metadata as __get_track_metadata, search_track_metadata as __search_track_metadata
from ..common.constants import ROUTE_TAGS, TRACK_SEARCH_FILTER_FIELD_MAP
from ..models.track_response_model import FILERTrackPagedResponse, FILERTrackResponse
from ..dependencies import InternalRequestParameters

TAGS = ROUTE_TAGS
router = APIRouter(
    prefix="/metadata",
    tags=TAGS,
    responses=RESPONSES
)

tags = TAGS + ["Track Metadata by ID"]
@router.get("/", tags=tags, response_model=FILERTrackResponse,
    name="Get metadata for multiple tracks",
    description="retrieve full metadata for one or more FILER track records")
async def get_track_metadata(
        track: Annotated[str, Query(description="comma separated list of one or more FILER track identifiers")],
        format: str= Depends(format_param),
        internal: InternalRequestParameters = Depends()) -> FILERTrackResponse:
    
    opts = HelperParameters(internal=internal, format=format, model=FILERTrackResponse, parameters=Parameters(track=track))
    return await __get_track_metadata(opts)

tags = TAGS + ['Record(s) by Text Search'] + ['Track Metadata by Text Search']
filter_param = FilterParameter(TRACK_SEARCH_FILTER_FIELD_MAP, ExpressionType.TEXT)
@router.get("/search", tags=tags, response_model=Union[BaseResponseModel, FILERTrackPagedResponse],
    name="Search for tracks", 
    description="find functional genomics tracks using category filters or by a keyword search against all text fields in the track metadata")
async def search_track_metadata(
        pagination: Annotated[PaginationParameters, Depends(PaginationParameters)],
        assembly: Assembly = Depends(assembly_param), 
        filter = Depends(filter_param), 
        keyword: str = Depends(keyword_param),
        format: str= Depends(format_param),
        countsOnly = Depends(counts_only_param),
        idsOnly = Depends(ids_only_param),
        internal: InternalRequestParameters = Depends(),
        ) -> Union[BaseResponseModel, FILERTrackPagedResponse]:
    
    if filter is None and keyword is None:
        raise RequestValidationError('must specify either a `filter` and/or a `keyword` to search')
    
    optionalParameters = Parameters(countsOnly=countsOnly, idsOnly=idsOnly)
    
    responseModel = BaseResponseModel if countsOnly or idsOnly else FILERTrackPagedResponse
    
    opts = HelperParameters(internal=internal, pagination=pagination,
        format=format, model=responseModel,
        parameters=Parameters(assembly=assembly, filter=filter, keyword=keyword, options=optionalParameters))
    
    return await __search_track_metadata(opts)


tags = TAGS + ["NIAGADS Genome Browser Configuration"]
@router.get("/browser_config", tags=tags,  response_model=Union[GenomeBrowserConfigResponse, GenomeBrowserExtendedConfigResponse],
    name="Get Genome Browser configuration for multiple tracks",
    description="retrieve NIAGADS Genome Browser track configuration for one or more FILER `track`(s) specified in the path")
async def get_track_browser_config(
        track: Annotated[str, Query(description="comma separated list of one or more FILER track identifiers")],
        inclMetadata: Optional[bool] = Query(default=False, description="include filterable track metadata for the track selector display"),
        format: str= Depends(format_param),
        internal: InternalRequestParameters = Depends()
        ) -> Union[GenomeBrowserConfigResponse, GenomeBrowserExtendedConfigResponse]:

    responseModel = GenomeBrowserExtendedConfigResponse if inclMetadata \
        else GenomeBrowserConfigResponse
    opts = HelperParameters(internal=internal, format=format, model=responseModel, parameters=Parameters(track=track))
    return await __get_track_metadata(opts)
