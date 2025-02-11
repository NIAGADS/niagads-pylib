from fastapi.datastructures import QueryParams
from pydantic import BaseModel, ConfigDict, Field
from typing import Any, Dict, List, Optional, Union, TypeVar
from fastapi.encoders import jsonable_encoder
from fastapi import Request
from hashlib import md5
from abc import ABC, abstractmethod

from niagads.utils.string import dict_to_string, xstr
from niagads.utils.dict import prune
from niagads.utils.reg_ex import regex_replace

from api.common.constants import JSON_TYPE
from api.common.enums import CacheKeyQualifier, CacheNamespace, OnRowSelect, ResponseContent, ResponseFormat, ResponseView
from api.common.formatters import id2title

class SerializableModel(BaseModel):
    def serialize(self, exclude: List[str] = None, promoteObjs=False, collapseUrls=False, groupExtra=False, byAlias=False):
        """Return a dict which contains only serializable fields.
        exclude -> list of fields to exclude
        promoteObjs -> when True expands JSON fields; i.e., ds = {a:1, b:2} becomes a:1, b:2 and ds gets dropped
        collapseUrls -> looks for field and field_url pairs and then updates field to be {url: , value: } object
        groupExtra -> if extra fields are present, group into a JSON object
        """
        data:dict = jsonable_encoder(self.model_dump(exclude=exclude, by_alias=byAlias)) # FIXME: not sure if encoder is necessary; check dates? maybe
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
    

class RowModel(SerializableModel, ABC):
    """
    NOTE: these abstract methods cannot be class methods 
    because sometimes the row models have extra fields 
    or objects that need to be promoted (e.g., experimental_design)
    that only exist when instantiated
    """
    
    @abstractmethod
    def get_view_config(self, view: ResponseView, **kwargs) -> JSON_TYPE:
        """ get configuration object required by the view """
        raise RuntimeError('`RowModel` is an abstract class; need to override abstract methods in child classes')
    
    @abstractmethod
    def to_view_data(self, view: ResponseView, **kwargs) -> JSON_TYPE:
        """ covert row data to view formatted data """
        raise RuntimeError('`RowModel` is an abstract class; need to override abstract methods in child classes')
    
    @abstractmethod
    def to_text(self, format: ResponseFormat, **kwargs) -> str:
        """ covert row data to a text string """
        raise RuntimeError('`RowModel` is an abstract class; need to override abstract methods in child classes')
    

class RequestDataModel(SerializableModel):
    request_id: str = Field(description="unique request identifier")
    endpoint: str = Field(description="queried endpoint")
    parameters: Dict[str, Union[int, str, bool]] = Field(description="request path and query parameters, includes unspecified defaults")
    message: Optional[List[str]] = Field(default=None, description="warning or info message qualifying the response")

    def add_message(self, message):
        if self.message is None:
            self.message = []
        self.message.append(message)   
        

    def update_parameters(self, params: BaseModel, exclude:List[str]=[]) -> str:
        """ default parameter values are not in the original request, so need to be added later """
        exclude = exclude + ['filter'] # do not overwrite original filter string with parsed tokens
        self.parameters.update(prune(params.model_dump(exclude=exclude)))
    
    @classmethod
    def sort_query_parameters(cls, params: dict, exclude:bool=False) -> str:
        """ called by cache_key method to alphabetize the parameters """
        if len(params) == 0:
            return ''
        sortedParams = dict(sorted(params.items())) # assuming Python 3+ where all dicts are ordered
        if exclude:
            for param in exclude:
                if param in sortedParams:
                    del sortedParams[param]
        return dict_to_string(sortedParams, nullStr='null', delimiter='&')
    

    @classmethod
    async def from_request(cls, request: Request):
        return cls(
            request_id=request.headers.get("X-Request-ID"),
            parameters=dict(request.query_params),
            endpoint=str(request.url.path)
        )

# TODO: create Enum for the namespaces
class CacheKeyDataModel(BaseModel, arbitrary_types_allowed=True):
    key: str # in memory cached key
    namespace: CacheNamespace = Field(description="namespace in the in-memory cache")
    
    @classmethod
    async def from_request(cls, request: Request):
        endpoint = str(request.url.path) # endpoint includes path parameters
        parameters = RequestDataModel.sort_query_parameters(dict(request.query_params), exclude=['format', 'view'])
        rawKey = endpoint + '?' + parameters.replace(':','_') # ':' delimitates keys in keydb
        
        # for pagination and 
        return cls(
            key = rawKey,
            namespace = CacheNamespace(request.url.path.split('/')[1])
        )
        

    def encrypt(self):
        return self.encrypt_key(self.key)
    
    
    def no_page(self):
        return self.remove_query_props(self.key, 'page')

    
    @staticmethod
    def remove_query_props(key:str, prop: str):
        pattern = r"\b" + prop + r"=[^&]*&?\s*"
        newKey = regex_replace(pattern, '', key)
        return regex_replace('&$', '', newKey) # remove terminal '&' if present
    
    
    @staticmethod
    def encrypt_key(key:str=None):
        return md5(key.encode('utf-8')).hexdigest()
    
    
class GenericDataModel(RowModel):
    """ Generic JSON Response """
    __pydantic_extra__: Dict[str, Any]  
    model_config = ConfigDict(extra='allow')
    
    def to_view_data(self, view: ResponseView, **kwargs):
        return self.model_dump()
    
    # FIXME: dates -> in xstr? maybe
    def to_text(self, format: ResponseFormat, **kwargs):
        nullStr = kwargs.get('nullStr', '.')
        match format:
            case ResponseFormat.TEXT:
                fields = list(self.model_dump().values())
                return '\t'.join([xstr(f, nullStr=nullStr, dictsAsJson=False) for f in fields])
            case _:
                raise NotImplementedError(f'Text transformation `{format.value}` not supported for a generic data response')
            
    
    def get_view_config(self, view: ResponseView, **kwargs):
        """ get configuration object required by the view """
        match view:
            case ResponseView.TABLE:
                self.get_table_view_config(kwargs)
            case ResponseView.IGV_BROWSER:
                return None
            case _:
                raise NotImplementedError(f'View `{view.value}` not yet supported for this response type')
            
        
    def get_table_view_config(self, **kwargs):
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
        
    
class PaginationDataModel(BaseModel):
    page: int = Field(default=1, description="if result is paged, indicates the current page of the result; defaults to 1")
    total_num_pages: int = Field(default=1, description="if the result is paged, reports total number of pages in the full result set (response); defaults to 1")
    paged_num_records: Optional[int] = Field(default=None, description="number of records in the current paged result set (response)")
    total_num_records: Optional[int] = Field(default=None, description="total number of records in the full result set (response)")

# possibly allows you to set a type hint to a class and all its subclasses
T_SerializableModel = TypeVar('T_SerializableModel', bound=SerializableModel)