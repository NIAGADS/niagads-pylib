from typing import Any, List, Optional, Union

from niagads.utils.string import dict_to_info_string
from pydantic import Field

from api.common.enums import ResponseFormat
from api.common.formatters import id2title

from .base_models import GenericDataModel, PagedResponseModel

class BEDFeature(GenericDataModel):
    chrom: str = Field(description="name of the chromosome or scaffold")
    chromStart: int = Field(description="starting position of the feature in the chromosomse. 0-based")
    chromEnd: int = Field(description="ending position of the feature; not included in the display")
    name: Optional[str] = Field(default='.', description="display label for the feature")
    score: Optional[Union[str, int, float]] = Field(default='.', description="a score between 0 and 1000")
    strand: Optional[str] = Field(default='.', description="forward (+) or reverse (-) direction")
    
    def to_view_data(self, view, **kwargs):
        match view:
            case view.TABLE:
                if kwargs['collapseExtras']:
                    data: dict = { k:v for k, v in self.model_dump().items() if k in list(self.model_fields.keys())}
                    extraData =  { k:v for k, v in self.model_dump().items() if k in list(self.model_extra.keys()) and k != 'track_id'}
                    data.update({'additional_fields': dict_to_info_string(extraData), 'track_id': self.track_id})
                    return data
                else:
                    return self.model_dump()
            case _:
                raise NotImplementedError(f'View `{view.value}` not yet supported for this response type')

    def get_view_config(self, view: ResponseFormat, **kwargs):
        """ get configuration object required by the view """
        match view:
            case view.TABLE:
                return self.__build_table_config(kwargs['collapseExtras'])
            case view.DATA_BROWSER:
                return {} # config needs request parameters (span)
            case _:
                raise NotImplementedError(f'View `{view.value}` not yet supported for this response type')
        
    def __build_table_config(self, collapseExtras:bool):
        """ Return a column and options object for niagads-viz-js/Table """
        fields = ['track_id'] + list(self.model_fields.keys()) 
        if len(self.model_extra) > 0:
            if collapseExtras: 
                fields = fields + ['additional_fields']
            else:
                fields += [k for k in self.model_extra.keys() if k != 'track_id']
                
        columns: List[dict] = [ {'id': f, 'header': id2title(f)} for f in fields]
        return {'columns': columns, 
            'options': { 'defaultColumns': fields[:8] }}
    

class BEDResponse(PagedResponseModel):
    response: List[BEDFeature]
    
    def to_view(self, view: ResponseFormat, **kwargs):
        dynamicExtras = False
        if view == view.TABLE:
            # need to override here b/c each row may have different fields
            extras = set()

            row: BEDFeature
            for row in self.response:
                if row.has_extras():
                    if len(extras) == 0:
                        extras = set(row.model_extra.keys())
                    else:
                        dynamicExtras = extras != set(row.model_extra.keys())
                        if dynamicExtras: break
        
        return super().to_view(view, collapseExtras=dynamicExtras, id=self.request.request_id)
