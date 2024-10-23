from fastapi import APIRouter, Depends, Path, Query, Request, status
from fastapi.encoders import jsonable_encoder
from typing import Annotated, List
from sqlalchemy.ext.asyncio import AsyncSession
import json

from api.dependencies.param_validation import convert_str2list, clean
from api.dependencies.location_params import span_param
from api.dependencies.exceptions import RESPONSES
from api.dependencies.shared_params import ResponseType
from api.response_models import BrowserTrack, VizTableResponse, VizTable, VizTableOptions, RequestDataModel, SerializableModel

from ..constants import ROUTE_TAGS,ROUTE_SESSION_MANAGER
from ..dependencies import MetadataQueryService, ApiWrapperService
from ..models import TrackPublic, InformativeTrackSummary

def serialize(model, record: SerializableModel):
    match model:
        case 'track':
            return TrackPublic(**record.serialize(expandObjs=True))
        case 'informative_track':
            return InformativeTrackSummary(**record.serialize(expandObjs=True))
        case 'browser_config':
            return BrowserTrack(**record.serialize())
        case _:
            raise KeyError('Invalid data model for NIAGADS-viz-js Table: %s' % model)       



TAGS = ROUTE_TAGS
router = APIRouter(
    prefix="/view",
    tags=TAGS,
    responses=RESPONSES
)

tags = TAGS + ["Redirect JSON responses to Visualization Tools"]
@router.get("/table/{data_model}", tags=tags, response_model=VizTableResponse,
    name="Serialize and cache query response for a NIAGADS-viz-js Table")
async def get_table_view(
        data_model: str,
        request: Request, # should have in memory store of the data
        forwardingRequestData: str, # serialized request data model 
    ) -> VizTableResponse:
    
    # get the original response from the request.session
    requestData = RequestDataModel(**json.loads(forwardingRequestData))
    # requestId = requestData.request_id
    responseData = [] # TODO: pulled from session
    # try to convert the data
    data = [ serialize(data_model, t) for t in responseData ] # convert Track to TrackPublic
    
    # build the table object
    columns = TrackPublic.table_columns()
    columnIds = [c['id'] for c in columns]   
    options = VizTableOptions(disableColumnFilters=True, defaultColumns=columnIds[:10])
    table = VizTable(id='tracks', data=data, columns=columns, options=options)
    
    response = VizTableResponse(request=requestData, response=table)
    #TODO - cache
    return response
   
