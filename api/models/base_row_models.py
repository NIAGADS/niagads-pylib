from abc import ABC, abstractmethod
from typing import Any, Dict, List, TypeVar
from pydantic import BaseModel, ConfigDict
from fastapi.encoders import jsonable_encoder

from niagads.utils.string import xstr

from api.common.enums import ResponseFormat, ResponseView
from api.common.formatters import id2title

class RowModel(BaseModel):
    """
    Most API responses are a lists of objects (rows).
    A Row Model defines the expected object.
    The RowModel base class defines class methods 
    expected for these objects to generate standardized API responses
    """
    
    def serialize(self, exclude: List[str] = None, promoteObjs=False, collapseUrls=False, groupExtra=False, byAlias=False):
        """
        basically a customized `model_dumps` but only when explicity called
        returns a dict which contains only serializable fields.
        exclude -> list of fields to exclude
        promoteObjs -> when True expands JSON fields; i.e., ds = {a:1, b:2} becomes a:1, b:2 and ds gets dropped
        collapseUrls -> looks for field and field_url pairs and then updates field to be {url: , value: } object
        groupExtra -> if extra fields are present, group into a JSON object
        """
        # note: encoder is necessary to correctly return enums/dates, etc
        data:dict = jsonable_encoder(self.model_dump(exclude=exclude, by_alias=byAlias)) 
        if promoteObjs:
            objFields = [k for k, v in data.items() if isinstance(v, dict)]
            for f in objFields:
                data.update(data.pop(f, None))

        if collapseUrls:
            fields = list(data.keys())
            pairedFields = [ f for f in fields if f + '_url' in fields]
            for f in pairedFields:
                data.update({f: {'url': data.pop(f +'_url', None), 'value': data[f]}})

        if groupExtra:
            raise NotImplementedError()  
        
        return data
    
    def has_extras(self):
        """ test if extra model fields are present """
        return len(self.model_extra) > 0
    
    
    def to_view_data(self, view: ResponseView, **kwargs):
        return self.model_dump()
    

    def to_text(self, format: ResponseFormat, **kwargs):
        nullStr = kwargs.get('nullStr', '.')
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
                self.__get_table_view_config(kwargs)
            case ResponseView.IGV_BROWSER:
                raise NotImplementedError('IGVBrowser view coming soon')
            case _:
                raise NotImplementedError(f'View `{view.value}` not yet supported for this response type')
            
        
    def __get_table_view_config(self, **kwargs):
        fields = list(self.model_dump().keys())
        columns: List[dict] = [ {'id': f, 'header': id2title(f)} for f in fields]
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
    
