from fastapi import APIRouter, Request
import json

from api.dependencies.exceptions import RESPONSES
from api.response_models import GenomeBrowserConfig, RequestDataModel, SerializableModel, \
    VizTableResponse, VizTable, VizTableOptions

from api.routers.filer.models import TrackPublic as FILERTrack, TrackOverlapSummary as FILERTrackOverlapSummary

def serialize(model, record: SerializableModel):
    match model:
        case 'filer_track':
            return FILERTrack(**record)
        case 'filer_overlaps_summary':
            return FILERTrackOverlapSummary(**record)
        case 'genome_browser_config':
            return GenomeBrowserConfig(**record)
        case _:
            raise KeyError('Invalid data model for NIAGADS-viz-js Table: %s' % model)       
        
def columns(model):
    match model:
        case 'filer_track':
            return FILERTrack.view_table_columns()
        case 'filer_overlaps_summary':
            return FILERTrackOverlapSummary.view_table_columns()
        case 'genome_browser_config':
            return GenomeBrowserConfig.view_table_columns()
        case _:
            raise KeyError('Invalid data model for NIAGADS-viz-js Table: %s' % model)       


TAGS = ['Views']
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
        forwardingRequestId: str, # serialized request data model 
    ) -> VizTableResponse:

    # get the original response from the request.session
    requestData = request.session.get(forwardingRequestId + '_request')
    requestData = request.session[forwardingRequestId + '_request']
    responseData = request.session[forwardingRequestId + '_response'] # TODO: pulled from session
    # try to convert the data
    data = [ serialize(data_model, t) for t in responseData ] # convert Track to TrackPublic
    
    # build the table object
    columns = columns(data_model)
    columnIds = [c['id'] for c in columns]   
    options = VizTableOptions(disableColumnFilters=True, defaultColumns=columnIds[:10])
    table = VizTable(id='tracks', data=data, columns=columns, options=options)
    
    response = VizTableResponse(request=requestData, response=table)
    #TODO - cache
    return response
   
