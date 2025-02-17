from pydantic import BaseModel, Field
from typing import Dict, List, Optional, Union
from fastapi import Request
from hashlib import md5

from niagads.utils.string import dict_to_string
from niagads.utils.dict import prune
from niagads.utils.reg_ex import regex_replace

from api.common.enums.cache import CacheNamespace

class RequestDataModel(BaseModel):
    request_id: str = Field(description="unique request identifier")
    endpoint: str = Field(description="queried endpoint")
    parameters: Dict[str, Union[int, str, bool]] = Field(description="request path and query parameters, includes unspecified defaults")
    message: Optional[List[str]] = Field(default=None, description="warning or info message qualifying the response")

    def add_message(self, message):
        if self.message is None:
            self.message = []
        self.message.append(message)   
        
        
    def set_request_id(self, id):
        self.request_id = id   


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

class CacheKeyDataModel(BaseModel, arbitrary_types_allowed=True):
    key: str # in memory cached key
    namespace: CacheNamespace = Field(description="namespace in the in-memory cache")
    
    @classmethod
    async def from_request(cls, request: Request):
        endpoint = str(request.url.path) # endpoint includes path parameters
        parameters = RequestDataModel.sort_query_parameters(dict(request.query_params), exclude=['format', 'view'])
        rawKey = endpoint + '?' + parameters.replace(':','_') # ':' delimitates keys in keydb
        
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
    
    

class PaginationDataModel(BaseModel):
    page: int = Field(default=1, description="if result is paged, indicates the current page of the result; defaults to 1")
    total_num_pages: int = Field(default=1, description="if the result is paged, reports total number of pages in the full result set (response); defaults to 1")
    paged_num_records: Optional[int] = Field(default=None, description="number of records in the current paged result set (response)")
    total_num_records: Optional[int] = Field(default=None, description="total number of records in the full result set (response)")

