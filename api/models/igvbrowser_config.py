from pydantic import ConfigDict, Field, computed_field
from sqlmodel import SQLModel
from typing import Any, Dict, Optional, List

from niagads.utils.list import find

from api.common.enums import OnRowSelect, ResponseFormat
from api.common.formatters import id2title
from api.models import BiosampleCharacteristics, ExperimentalDesign
from api.models.base_models import GenericDataModel, RowModel
from api.models.base_response_models import PagedResponseModel, BaseResponseModel

class IGVBrowserTrackConfig(SQLModel, RowModel):
    track_id: str = Field(serialization_alias="id")
    browser_track_name: str = Field(serialization_alias="name")  
    url: str 
    description: str
    index_url: str = Field(serialization_alias ='indexURL')
    browser_track_type: str = Field(serialization_alias = 'type')
    browser_track_format: str = Field(serialization_alias ='format')
    
    # model_config = ConfigDict(populate_by_name=True)

    def get_view_config(self, view: ResponseFormat, **kwargs):
        """ get configuration object required by the view """
        return None
    
    def to_view_data(self, view: ResponseFormat, **kwargs):
        return self.model_dump(by_alias=True)


# sole purpose of this model is to assemble the information for the track selector
class IGVBrowserTrackMetadata(RowModel):
    track_id: str
    name: str
    description: str
    data_source: str
    feature_type: str = Field(serialization_alias='feature')
    biosample_characteristics: BiosampleCharacteristics
    experimental_design: ExperimentalDesign
    
    # model_config = ConfigDict(populate_by_name=True)
    
    @classmethod
    def get_table_columns(self):
        fields = list(self.model_fields.keys())
        columns: List[dict] = [ {'id': f, 'header': id2title(f)} for f in fields if f not in ['biosample_characteristics', 'experimental_design'] ] 
        columns += [ {'id': f, 'header': id2title(f)} for f in BiosampleCharacteristics.model_fields]
        columns += [ {'id': f, 'header': id2title(f)} for f in ExperimentalDesign.model_fields]

        return columns
    
    @classmethod
    def get_table_options(self):
        options: dict = {
            'rowSelect': {
                'header': 'Add/Remove Track',
                'enableMultiRowSelect': True,
                'rowId': 'track_id',
                'onRowSelectAction': str(OnRowSelect.UPDATE_GENOME_BROWSER)
            }
        }
        return options
    
    def get_view_config(self, view: ResponseFormat, **kwargs):
        """ get configuration object required by the view """
        return None
    
    def to_view_data(self, view: ResponseFormat, **kwargs):
        return self.model_dump(by_alias=True)
        


    
# TODO: allowable views: direct to genome browser   
# TODO: create truncated response instead of paging
class IGVBrowserTrackConfigResponse(PagedResponseModel):
    response: List[IGVBrowserTrackConfig]
    
    def to_view(self, view, **kwargs):
        raise NotImplementedError('IGVBrowser view coming soon')
        # return super().to_view(view, **kwargs)
        # NOTE: super().to_view call w/result in error; expects non null config
    
class IGVBrowserApplicationConfigResponse(PagedResponseModel):
    response: Dict[str, Any]
    
    @classmethod
    def build_application_config(cls, metadata: RowModel):
        tableData = []
        config = []
        track: RowModel
        for track in metadata:
            rowData = track.serialize()
            config.append(IGVBrowserTrackConfig(**rowData).to_view_data(ResponseFormat.JSON))
            rowData = IGVBrowserTrackMetadata(**rowData)
            tableData.append(rowData.serialize(promoteObjs=True, byAlias=True))
                        
        columns = IGVBrowserTrackMetadata.get_table_columns()
        options = IGVBrowserTrackMetadata.get_table_options()

        return {
            'track_config': config,
            'track_selector_table': {'data': tableData, 'columns': columns, 'options': options}
        }
        
            
    def to_view(self, view, **kwargs):
        raise NotImplementedError('IGVBrowser view coming soon')
        # return super().to_view(view, **kwargs)
        # NOTE: super().to_view call w/result in error
