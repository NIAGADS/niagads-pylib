from pydantic import Field, computed_field
from sqlmodel import SQLModel
from typing import List, Optional

from api.common.enums.response_properties import OnRowSelect, ResponseFormat, ResponseView
from api.common.formatters import id2title
from api.config.settings import get_settings
from api.models.base_response_models import BaseResponseModel
from api.models.base_row_models import RowModel
from api.models.track_properties import BiosampleCharacteristics, ExperimentalDesign
from api.models.view_models import TableViewModel


class IGVBrowserTrackConfig(SQLModel, RowModel):
    track_id: str = Field(serialization_alias="id")
    browser_track_name: str = Field(serialization_alias="name")  
    url: str 
    description: str
    index_url: str = Field(serialization_alias ='indexURL')
    browser_track_type: str = Field(serialization_alias = 'type')
    browser_track_format: str = Field(serialization_alias ='format')
    infoURL: str = get_settings().IGV_BROWSER_INFO_URL
    
    @computed_field
    @property
    def autoscale(self) -> bool:
        return self.browser_track_type == 'qtl'
    
    # model_config = ConfigDict(populate_by_name=True)

    def get_view_config(self, view: ResponseView, **kwargs):
        """ get configuration object required by the view """
        return None
    
    def to_view_data(self, view: ResponseView, **kwargs):
        return self.model_dump(by_alias=True)
    
    def to_text(self, format: ResponseFormat, **kwargs):
        return super().to_text(format, **kwargs)


# sole purpose of this model is to assemble the information for the track selector
class IGVBrowserTrackMetadata(RowModel):
    track_id: str
    name: str
    description: str
    data_source: str
    feature_type: str # = Field(serialization_alias='feature')
    biosample_characteristics: Optional[BiosampleCharacteristics] = None
    experimental_design: Optional[ExperimentalDesign] = None
    
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
            },
        }
        return options
    
    def get_view_config(self, view: ResponseView, **kwargs):
        """ get configuration object required by the view """
        return None
    



class IGVBrowserTrackConfigResponse(BaseResponseModel):
    data: List[IGVBrowserTrackConfig]
    

    
class IGVBrowserTrackSelectorResponse(BaseResponseModel):
    data: TableViewModel
    
    @classmethod
    def build_table(cls, metadata: RowModel, tableId: str):
        tableData = []
        track: RowModel
        for track in metadata:
            rowData = track.serialize()
            rowData = IGVBrowserTrackMetadata(**rowData)
            tableData.append(rowData.serialize(promoteObjs=True, byAlias=True))
                        
        columns = IGVBrowserTrackMetadata.get_table_columns()
        options = IGVBrowserTrackMetadata.get_table_options()
        options.update({'defaultColumns': [c['id'] for c in columns[:8]]})

        return {'data': tableData, 'columns': columns, 'options': options, 'id': tableId}
        


