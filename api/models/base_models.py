from fastapi.datastructures import QueryParams
from pydantic import BaseModel, ConfigDict, Field
from typing import Any, Dict, List, Optional, Union, TypeVar
from fastapi.encoders import jsonable_encoder
from fastapi import Request
from hashlib import md5
from abc import ABC, abstractmethod

from niagads.utils.string import dict_to_string
from niagads.utils.dict import prune

from api.common.constants import JSON_TYPE
from api.common.enums import CacheNamespace, OnRowSelect, ResponseFormat
from api.common.formatters import id2title


    

class SerializableModel(BaseModel):
    def serialize(self, exclude: List[str] = None, promoteObjs=False, collapseUrls=False, groupExtra=False):
        """Return a dict which contains only serializable fields.
        exclude -> list of fields to exclude
        promoteObjs -> when True expands JSON fields; i.e., ds = {a:1, b:2} becomes a:1, b:2 and ds gets dropped
        collapseUrls -> looks for field and field_url pairs and then updates field to be {url: , value: } object
        groupExtra -> if extra fields are present, group into a JSON object
        """
        data:dict = jsonable_encoder(self.model_dump(exclude=exclude)) # FIXME: not sure if encoder is necessary; check dates? maybe
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
    def get_view_config(self, view: ResponseFormat, **kwargs) -> JSON_TYPE:
        """ get configuration object required by the view """
        raise RuntimeError('`RowModel` is an abstract class; need to override abstract methods in child classes')
    
    @abstractmethod
    def to_view_data(self, view: ResponseFormat, **kwargs) -> JSON_TYPE:
        """ covert row data to view formatted data """
        raise RuntimeError('`RowModel` is an abstract class; need to override abstract methods in child classes')
    

class RequestDataModel(SerializableModel):
    request_id: str = Field(description="unique request identifier")
    endpoint: str = Field(description="queried endpoint")
    parameters: Dict[str, Union[int, str, bool]] = Field(description="request path and query parameters, includes unspecified defaults")
    msg: Optional[str] = Field(default=None, description="warning or info message qualifying the response")
    
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
    internal: str = Field(description="in-memory cache key for internal access to cached data")
    internal_raw: str = Field(default=None, description="in-memory cache key for cached raw data / no pagination or formatting")
    external: str = Field(description="in-memory cache key for external access to a cached response")
    namespace: CacheNamespace = Field(description="namespace in the in-memory cache")
    
    @classmethod
    async def from_request(cls, request: Request):
        endpoint = str(request.url.path) # endpoint includes path parameters
        parameters = RequestDataModel.sort_query_parameters(dict(request.query_params))
        internalCacheKey = endpoint + '?' + parameters.replace(':','_') # ':' delimitates keys in keydb
        
        # for 'raw' results; remove pagination and formatting 
        parameters = RequestDataModel.sort_query_parameters(dict(request.query_params), exclude=['format', 'page', 'content'])
        internalRawCacheKey = endpoint + '?' + parameters.replace(':', '_')
        
        return cls(
            internal = internalCacheKey,
            internal_raw = internalRawCacheKey,
            external = md5(internalCacheKey.encode('utf-8')).hexdigest(), # so that it is unique to the endpoint + params, unlike distinct requestId
            namespace = CacheNamespace(request.url.path.split('/')[2]) \
                if '/redirect/' in request.url.path \
                    else CacheNamespace(request.url.path.split('/')[1])
        )

# FIXME: 'Any' or 'SerializableModel' for response
class AbstractResponse(ABC, SerializableModel):
    response: Any = Field(description="result (data) from the request")
    
    @abstractmethod 
    def to_view(self, view:ResponseFormat, **kwargs):
        """ transform response to JSON expected by NIAGADS-viz-js Table """
        if len(self.response) == 0:
            raise RuntimeError('zero-length response; cannot generate view')
        if 'on_row_select' not in kwargs:
            if 'num_overlaps' in self.response[0].model_fields.keys() or \
                'num_overlaps' in self.response[0].model_extra.keys():
                kwargs['on_row_select'] = OnRowSelect.ACCESS_ROW_DATA
                
        viewResponse: Dict[str, Any] = {}
        data = []
        row: RowModel # annotated type hint
        for index, row in enumerate(self.response):
            if index == 0:
                viewResponse = row.get_view_config(view, **kwargs)
            data.append(row.to_view_data(view, **kwargs))
        viewResponse.update({'data': data})
    
        if view == ResponseFormat.TABLE:
            viewResponse.update({'id': kwargs['id']})
            
        return viewResponse



class GenericDataModel(RowModel):
    """ Generic JSON Response """
    __pydantic_extra__: Dict[str, Any]  
    model_config = ConfigDict(extra='allow')
    
    def to_view_data(self, view, **kwargs):
        return self.model_dump()
    
    def get_view_config(self, view, **kwargs):
        """ get configuration object required by the view """
        match view:
            case view.TABLE:
                self.get_table_view_config(kwargs)
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
    key: Optional[str] = Field(default=None, description="encrypted keyset for key-based pagination") 


# possibly allows you to set a type hint to a class and all its subclasses
T_SerializableModel = TypeVar('T_SerializableModel', bound=SerializableModel)