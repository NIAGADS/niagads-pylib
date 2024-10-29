from fastapi.encoders import jsonable_encoder
from sqlmodel import SQLModel
from typing import Optional, Dict, List, Union
from typing_extensions import Self

from api.common.constants import JSON_TYPE
from api.common.enums import ResponseFormat
from api.common.formatters import id2title

from .base_models import BaseResponseModel, RowModel

class GenomeBrowserConfig(RowModel, SQLModel):
    track_id: str
    name: str
    browser_track_format: Optional[str]
    url: str
    index_url: Optional[str]
    
    def get_view_config(self, view: ResponseFormat) -> dict:
        """ get configuration object required by the view """
        match view:
            case view.TABLE:
                return self.__build_table_config()
            case _:
                raise NotImplementedError(f'View `{view.value}` not yet supported for this response type')

    def to_view_data(self, view: ResponseFormat) -> dict:
        # TODO match on response type for data transformations?
        return self.model_dump()

    def __build_table_config(self):
        """ Return a column and options object for niagads-viz-js/Table """
        fields = list(self.model_fields.keys())
        columns: List[dict] = [ {'id': f, 'header': id2title(f)} for f in fields] 
        # FIXME: maybe add these on the genome browser side of things in the javascript
        options: dict = {
            'disableColumnFilters': True, # FIXME: Remove when column filters are implemented
            'rowSelect': {
                'header': 'Show/Hide Track',
                'enableRowMultiSelect': True,
                'rowId': 'track_id'
            }
        }
        return {'columns': columns, 'options': options}
    
class GenomeBrowserExtendedConfig(GenomeBrowserConfig):
    description: Optional[str]
    feature_type: str
    data_source: str
    browser_track_category: Optional[str]
    biosample_characteristics: Optional[Dict[str, str]]
    experimental_design: Optional[Dict[str, str]]
    
    def to_view_data(self, view: ResponseFormat) -> dict:
        # TODO match on response type for data transformations?
        return self.serialize(promoteObjs=True)
    
    def get_view_config(self, view: ResponseFormat) -> dict:
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
            fields += list(self.biosample_characteristics.keys())
        if self.experimental_design is not None:
            fields += list(self.experimental_design.keys())
            
        columns: List[dict] = [ {'id': f, 'header': id2title(f)} for f in fields] 
        # FIXME: maybe add these on the genome browser side of things in the javascript
        options: dict = {
            'disableColumnFilters': True, # FIXME: Remove when column filters are implemented
            'rowSelect': {
                'header': 'Show/Hide Track',
                'enableRowMultiSelect': True,
                'rowId': 'track_id'
            }
        }
        return {'columns': columns, 'options': options}
    
    
class GenomeBrowserConfigResponse(BaseResponseModel):
    response: List[GenomeBrowserConfig]
    
class GenomeBrowserExtendedConfigResponse(BaseResponseModel):
    response: List[GenomeBrowserExtendedConfig]

