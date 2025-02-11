from typing import Any, List, Optional, Union

from niagads.utils.string import dict_to_info_string, xstr
from pydantic import Field

from api.common.enums import ResponseFormat, ResponseView
from api.common.formatters import id2title

from api.models.base_response_models import PagedResponseModel
from api.models.base_models import GenericDataModel

class BEDFeature(GenericDataModel):
    chrom: str = Field(description="name of the chromosome or scaffold")
    chromStart: int = Field(description="starting position of the feature in the chromosomse. 0-based")
    chromEnd: int = Field(description="ending position of the feature; not included in the display")
    name: Optional[str] = Field(default='.', description="display label for the feature")
    score: Optional[Union[str, int, float]] = Field(default='.', description="a score between 0 and 1000")
    strand: Optional[str] = Field(default='.', description="forward (+) or reverse (-) direction")
    
    
    def add_track(self, trackId: Any):
        self.model_extra['track_id'] = trackId
        

    def to_text(self, format: ResponseFormat, **kwargs):
        nullStr = kwargs.get('nullStr', '.')
        data = self.__get_row_data(kwargs.get('collapseExtras', False))
        return '\t'.join([xstr(value, nullStr=nullStr, dictsAsJson=False) for value in data.values()])
    
    
    def __get_row_data(self, collapseExtras: bool):
        if collapseExtras:
            data: dict = { k:v for k, v in self.model_dump().items() if k in list(self.model_fields.keys())}
            extraData =  { k:v for k, v in self.model_dump().items() if k in list(self.model_extra.keys()) and k != 'track_id'}
            data.update({'additional_fields': dict_to_info_string(extraData), 'track_id': self.track_id})
            return data
        else:
            return self.model_dump()


    def get_field_names(self, collapseExtras: bool):
        """ get list of valid fields """
        fields = list(self.model_fields.keys())
        if len(self.model_extra) > 0:
            if collapseExtras: 
                fields = fields + ['additional_fields']
            else:
                fields += [k for k in self.model_extra.keys() if k != 'track_id']
                
        fields = fields + ['track_id']
        return fields
    
    
    def to_view_data(self, view: ResponseView, **kwargs):
        match view:
            case view.TABLE:
                return self.__get_row_data(kwargs.get('collapseExtras', False))
            case _:
                raise NotImplementedError(f'View `{view.value}` not yet supported for this response type')


    def get_view_config(self, view: ResponseView, **kwargs):
        """ get configuration object required by the view """
        match view:
            case view.TABLE:
                return self.__build_table_config(kwargs.get('collapseExtras', False))
            #case view.IGV_BROWSER:
            #    return {} # config needs request parameters (span)
            case _:
                raise NotImplementedError(f'View `{view.value}` not yet supported for this response type')
        
    def __build_table_config(self, collapseExtras:bool):
        """ Return a column and options object for niagads-viz-js/Table """
        
        fields = self.get_field_names(collapseExtras)          
        columns: List[dict] = [ {'id': f, 'header': id2title(f)} for f in fields]
        return {'columns': columns, 
            'options': { 'defaultColumns': fields[:8] }}
    

class BEDResponse(PagedResponseModel):
    response: List[BEDFeature]
    
    def __has_dynamic_extras(self) -> bool:
        """ test to see if rows have different additional fields """
        extras = set()

        row: BEDFeature
        for row in self.response:
            if row.has_extras():
                if len(extras) == 0:
                    extras = set(row.model_extra.keys())
                else:
                    dynamicExtras = extras != set(row.model_extra.keys())
                    if dynamicExtras: return True
        
        return False
                    
                    
    def to_text(self, format: ResponseFormat, **kwargs):
        """ return a text response (e.g., BED, plain text) """
        hasDynamicExtras = self.__has_dynamic_extras()
        return super().to_text(format, fields=self.response[0].get_field_names(collapseExtras=hasDynamicExtras), 
            collapseExtras=hasDynamicExtras, **kwargs)
    
    
    def to_view(self, view: ResponseView, **kwargs):
        return super().to_view(view, collapseExtras=self.__has_dynamic_extras(), **kwargs)
