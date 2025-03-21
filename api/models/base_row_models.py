from typing import Any, Dict, List, TypeVar
from pydantic import ConfigDict

from niagads.utils.string import xstr

from api.common.constants import DEFAULT_NULL_STRING
from api.common.enums.response_properties import ResponseFormat, ResponseView
from api.common.formatters import id2title
from api.models.base_models import SerializableModel
from api.models.view_models import TableColumn

class RowModel(SerializableModel):
    """
    Most API responses are a lists of objects (rows).
    A Row Model defines the expected object.
    The RowModel base class defines class methods 
    expected for these objects to generate standardized API responses
    """
    
    @classmethod
    def get_model_fields(cls):
        return list(cls.model_fields.keys())
    
    def has_extras(self):
        """ test if extra model fields are present """
        return len(self.model_extra) > 0
    
    
    def to_view_data(self, view: ResponseView, **kwargs):
        return self.model_dump()
    

    def to_text(self, format: ResponseFormat, **kwargs):
        nullStr = kwargs.get('nullStr', DEFAULT_NULL_STRING)
        match format:
            case ResponseFormat.TEXT:
                values = list(self.model_dump().values())
                return '\t'.join([xstr(v, nullStr=nullStr, dictsAsJson=False) for v in values])
            case _:
                raise NotImplementedError(f'Text transformation `{format.value}` not supported for a generic data response')
            
    
    def get_view_config(self, view: ResponseView, **kwargs):
        """ get configuration object required by the view """
        match view:
            case ResponseView.TABLE:
                return self.__get_table_view_config(**kwargs)
            case ResponseView.IGV_BROWSER:
                raise NotImplementedError('IGVBrowser view coming soon')
            case _:
                raise NotImplementedError(f'View `{view.value}` not yet supported for this response type')
            
        
    def __get_table_view_config(self, **kwargs):
        fields = list(self.model_dump().keys())
        columns: List[TableColumn] = [ TableColumn(id=f, header=id2title(f)) for f in fields]
        options =  {}

        if 'track_id' in fields:
            countsPresent = any([True for f in fields if f.startswith('num_')])
            if countsPresent:
                options.update({'rowSelect': {
                        'header': 'Select',
                        'enableMultiRowSelect': True,
                        'rowId': 'track_id',
                        'onRowSelectAction': kwargs['on_row_select']
                    }})
        return {'columns': columns, 'options': options}


    
# allows you to set a type hint to a class and all its subclasses 
# as long as type is specified as Type[T_RowModel] 
# Type: from typing import Type
T_RowModel = TypeVar('T_RowModel', bound=RowModel)


class GenericDataModel(RowModel):
    """ a row model that allows for extra, unknown fields  """
    __pydantic_extra__: Dict[str, Any]  
    model_config = ConfigDict(extra='allow')
    
