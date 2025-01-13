from pydantic import ConfigDict, Field
from sqlmodel import SQLModel
from typing import Optional, List

from niagads.utils.list import find

from api.common.enums import OnRowSelect, ResponseFormat
from api.common.formatters import id2title

from .base_models import RowModel
from .base_response_models import PagedResponseModel
from .biosample_characteristics import BiosampleCharacteristics
from .experimental_design import ExperimentalDesign 

class IGVBrowserConfig(RowModel,SQLModel):
    track_id: str = Field(alias='id')
    browser_track_name: str = Field(alias='name')  
    url: str 
    description: str
    index_url: str = Field(alias='indexUrl')
    browser_track_type: str = Field(alias='type')
    browser_track_format: str = Field(alias='format')
    
    model_config = ConfigDict(populate_by_name=True)

    def get_view_config(self, view: ResponseFormat, options:dict = None) -> dict:
        """ get configuration object required by the view """
        match view:
            case view.TABLE:
                return self._build_table_config()
            case _:
                raise NotImplementedError(f'View `{view.value}` not yet supported for this response type')

    def to_view_data(self, view: ResponseFormat, **kwargs) -> dict:
        # TODO match on response type for data transformations?
        return self.model_dump()

    def _build_table_config(self):
        """ Return a column and options object for niagads-viz-js/Table """
        fields = list(self.model_fields.keys())
        columns: List[dict] = [ {'id': f, 'header': id2title(f)} for f in fields] 
        
        # FIXME: maybe add these on the genome browser side of things in the javascript
        options: dict = {
            'rowSelect': {
                'header': 'Add/Remove Track',
                'enableMultiRowSelect': True,
                'rowId': 'track_id',
                'onRowSelectAction': OnRowSelect.UPDATE_GENOME_BROWSER
            }
        }
        return {'columns': columns, 'options': options}
    
class IGVBrowserExtendedConfig(IGVBrowserConfig):
    description: Optional[str]
    feature_type: str
    data_source: str
    browser_track_category: Optional[str]
    subject_phenotype: Optional[dict] = None# TODO: for genomicsdb; need to create Phenotype type
    biosample_characteristics: Optional[BiosampleCharacteristics] 
    experimental_design: Optional[ExperimentalDesign]
    
    def to_view_data(self, view: ResponseFormat, **kwargs) -> dict:
        # TODO match on response type for data transformations?
        return self.serialize(promoteObjs=True)
    
    def get_view_config(self, view: ResponseFormat, **kwargs) -> dict:
        """ get configuration object required by the view """
        match view:
            case view.TABLE:
                return self.__build_table_config()
            case _:
                raise NotImplementedError(f'View `{view.value}` not yet supported for this response type')
    
    def __build_table_config(self):
        """ Return a column and options object for niagads-viz-js/Table """
        fields = [k for k in self.model_fields.keys() if k not in ['biosample_characteristics', 'experimental_design']]
        if self.biosample_characteristics is not None:
            fields += list(BiosampleCharacteristics.model_fields.keys())
        if self.experimental_design is not None:
            fields += list(ExperimentalDesign.model_fields.keys())
            
        columns: List[dict] = [ {'id': f, 'header': id2title(f)} for f in fields] 
        # update type of is_lifted to boolean
        index: int = find(columns, 'is_lifted', 'id', returnValues=False)
        columns[index[0]].update({'type': 'boolean', 'description': 'data have been lifted over from an earlier genome build'})
        
        # FIXME: maybe add these on the genome browser side of things in the javascript
        options: dict = {
            'rowSelect': {
                'header': 'Add/Remove Track',
                'enableMultiRowSelect': True,
                'rowId': 'track_id',
                'onRowSelectAction': OnRowSelect.UPDATE_GENOME_BROWSER
            }
        }
        return {'columns': columns, 'options': options}
    
    
class IGVBrowserConfigResponse(PagedResponseModel):
    response: List[IGVBrowserConfig]
    
    def to_view(self, view, **kwargs):
        return super().to_view(view, **kwargs)
    
class IGVBrowserExtendedConfigResponse(PagedResponseModel):
    response: List[IGVBrowserExtendedConfig]
    
    def to_view(self, view, **kwargs):
        return super().to_view(view, **kwargs)

