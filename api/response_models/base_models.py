from pydantic import BaseModel, ConfigDict
from typing import Any, Dict, Optional, Type, Union, TypeVar
from typing_extensions import Self
from fastapi.encoders import jsonable_encoder
from fastapi import Request
from urllib.parse import parse_qs
from hashlib import md5

from niagads.utils.string import dict_to_string

from api.common.constants import JSON_TYPE
from api.common.enums import CacheNamespace, ResponseFormat

class SerializableModel(BaseModel):
    def serialize(self, promoteObjs=False, collapseUrls=False, groupExtra=False):
        """Return a dict which contains only serializable fields.
        promoteObjs -> when True expands JSON fields; i.e., ds = {a:1, b:2} becomes a:1, b:2 and ds gets dropped
        collapseUrls -> looks for field and field_url pairs and then updates field to be {url: , value: } object
        groupExtra -> if extra fields are present, group into a JSON object
        """
        data:dict = jsonable_encoder(self.model_dump()) # FIXME: not sure if encoder is necessary; check dates? maybe
        if promoteObjs:
            objFields = [ k for k, v in data.items() if isinstance(v, dict)]
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
    

class RowModel(SerializableModel):
    """
    NOTE: these abstract methods cannot be class methods 
    because sometimes the row models have extra fields 
    or objects that need to be promoted (e.g., experimental_design)
    that only exist when instantiated
    """
    def get_view_config(self, view: ResponseFormat) -> JSON_TYPE:
        """ get configuration object required by the view """
        raise NotImplementedError('`RowModel` is an abstract class; override in child classes')
    
    def to_view_data(self, view: ResponseFormat) -> JSON_TYPE:
        """ covert row data to view formatted data """
        raise NotImplementedError('`RowModel` is an abstract class; override in child classes')

    
class RequestDataModel(SerializableModel):
    request_id: str
    endpoint: str
    parameters: Dict[str, Union[int, str, bool]]
    msg: Optional[str] = None
    
    @classmethod
    def sort_query_parameters(cls, params: dict) -> str:
        """ called by cache_key method to alphabetize the parameters """
        if len(params) == 0:
            return ''
        sortedParams = dict(sorted(params.items())) # assuming Python 3+ where all dicts are ordered
        return dict_to_string(sortedParams, nullStr='null', delimiter='&')
    
    @classmethod
    async def from_request(cls, request: Request):
        return cls(
            request_id=request.headers.get("X-Request-ID"),
            parameters=dict(request.query_params),
            endpoint=str(request.url.path)
        )

class CacheKeyDataModel(BaseModel, arbitrary_types_allowed=True):
    internal: str
    external: str
    namespace: CacheNamespace
    
    @classmethod
    async def from_request(cls, request: Request):
        parameters = RequestDataModel.sort_query_parameters(dict(request.query_params))
        endpoint = str(request.url.path) # endpoint includes path parameters
        internalCacheKey = endpoint + '?' + parameters.replace(':','_') # ':' delimitates keys in keydb
        return cls(
            internal = internalCacheKey,
            external = md5(internalCacheKey.encode('utf-8')).hexdigest(), # so that it is unique to the endpoint + params, unlike distinct requestId
            namespace = CacheNamespace(request.url.path.split('/')[1])
        )

        
class BaseResponseModel(SerializableModel):
    request: RequestDataModel
    response: Any
        
    def to_view(self, view:ResponseFormat):
        """ transform response to JSON expected by NIAGADS-viz-js Table """
        if len(self.response) == 0:
            raise RuntimeError('zero-length response; cannot generate view')
        
        viewResponse: Dict[str, Any] = {}
        data = []
        row: RowModel # annotated type hint
        for index, row in enumerate(self.response):
            if index == 0:
                viewResponse = row.get_view_config(view)
            data.append(row.to_view_data(view))
        viewResponse.update({'data': data})
    
        if view == ResponseFormat.TABLE:
            viewResponse.update({'id': self.request.request_id})
            
        return viewResponse

        
    @classmethod
    def row_model(cls: Self, name=False):
        """ get the type of the row model in the response """
        
        rowType = cls.model_fields['response'].annotation
        try: # can't explicity test for List[rowType], so just try
            rowType = rowType.__args__[0] # rowType = typing.List[RowType]
        except:
            rowType = rowType
        
        return rowType.__name__ if name == True else rowType
    
    @classmethod
    def is_paged(cls: Self):
        return 'pagination' in cls.model_fields



class GenericDataModel(SerializableModel):
    """ Generic JSON Response """
    __pydantic_extra__: Dict[str, Any]  
    model_config = ConfigDict(extra='allow')
    
    
class PaginationDataModel(BaseModel):
    page: int = 1
    total_num_pages: int = 1
    paged_num_records: int 
    total_num_records: int

class PagedResponseModel(BaseResponseModel):
    pagination: Optional[PaginationDataModel] = None



# possibly allows you to set a type hint to a class and all its subclasses
T_SerializableModel = TypeVar('T_SerializableModel', bound=SerializableModel)
T_BaseResponseModel = TypeVar('T_BaseResponseModle', bound=BaseResponseModel)