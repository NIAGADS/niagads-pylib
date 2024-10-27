from fastapi import APIRouter, Request
from enum import Enum

from api.common.exceptions import RESPONSES
from api.response_models import GenomeBrowserConfig, SerializableModel, \
    VizTableResponse, VizTable, VizTableOptions

from api.routers.filer.models.track_response_model import FILERTrackBrief, FILERTrack, FILERTrackOverlapSummary

class RowModel(Enum):
    FILERTrackBrief = FILERTrackBrief
    FILERTrack = FILERTrack
    FILERTrackOverlapSummary = FILERTrackOverlapSummary
    GenomeBrowserConfig = GenomeBrowserConfig
    

def serialize(model: RowModel, record: SerializableModel):
    try:
        return model.value(**record)
    except:
        raise RuntimeError('Invalid data model for NIAGADS-viz-js Table: %s' % model)       
        
def columns(model: RowModel):
    try:
        return model.value.view_table_columns()
    except:
        raise RuntimeError('Invalid data model for NIAGADS-viz-js Table: %s' % model)       
    """
    match model:
        case 'filer_track':
            return FILERTrack.view_table_columns()
        case 'filer_overlaps_summary':
            return FILERTrackOverlapSummary.view_table_columns()
        case 'genome_browser_config':
            return GenomeBrowserConfig.view_table_columns()
        case _:
    """
            


TAGS = ['Views']
router = APIRouter(
    prefix="/view",
    tags=TAGS,
    responses=RESPONSES
)

tags = TAGS + ["Redirect JSON responses to Visualization Tools"]
@router.get("/table/{row_model}", tags=tags, response_model=VizTableResponse,
    name="Serialize and cache query response for a NIAGADS-viz-js Table")
async def get_table_view(
        row_model: str,
        request: Request, # should have in memory store of the data
        forwardingRequestId: str, # serialized request data model 
    ) -> VizTableResponse:

    # get the original response from the request.session
    try:
        # FIXME: use cache
        requestData = request.session.get(forwardingRequestId + '_request')
        requestData = request.session[forwardingRequestId + '_request']
        responseData = request.session[forwardingRequestId + '_response'] # TODO: pulled from session
        # try to convert the data
        data = [ serialize(row_model, t) for t in responseData ] # convert Track to TrackPublic
        
        # build the table object
        columns = columns(row_model)
        columnIds = [c['id'] for c in columns]   
        options = VizTableOptions(disableColumnFilters=True, defaultColumns=columnIds[:10])
        table = VizTable(id='tracks', data=data, columns=columns, options=options)
        
        response = VizTableResponse(request=requestData, response=table)
        #TODO - cache
        return response
    except:
        raise NotImplementedError('Interactive table view coming soon')
    finally:
        # TODO: any session clean up in case of error?
        pass
