"""Models defining custom types for Response Model class attributes"""
from typing import Dict, List, Optional, Type, Union

from fastapi import Request
from fastapi.exceptions import RequestValidationError
from niagads.dict_utils.core import prune
from niagads.open_access_api_cache_manager.core import CacheNamespace
from niagads.open_access_api_configuration.constants import ALLOWABLE_VIEW_RESPONSE_CONTENTS
from niagads.open_access_api_models.responses.core import ResponseModel, T_ResponseModel
from niagads.open_access_api_parameters.response import (
    ResponseContent,
    ResponseFormat,
    ResponseView,
)
from niagads.string_utils.core import blake2b_hash, dict_to_string, regex_replace
from pydantic import BaseModel, Field, field_validator, model_validator


class RequestDataModel(BaseModel):
    """Captures cleaned user-centric information about the origining request."""
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
        """ add default parameter values that are not included in the originating request """
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
    """Generates and stores cache key for the response, given the originating request.
    
    includes member and static functions for 
    encyption of keys and removing view related query props
    """
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
        return blake2b_hash(key)
    

class PaginationDataModel(BaseModel):
    """Captures pagination status."""
    page: int = Field(default=1, description="if result is paged, indicates the current page of the result; defaults to 1")
    total_num_pages: int = Field(default=1, description="if the result is paged, reports total number of pages in the full result set (response); defaults to 1")
    paged_num_records: Optional[int] = Field(default=None, description="number of records in the current paged result set (response)")
    total_num_records: Optional[int] = Field(default=None, description="total number of records in the full result set (response)")


class ResponseConfiguration(BaseModel, arbitrary_types_allowed=True):
    """Captures response-related parameter values (format, content, view) and model"""
    format: ResponseFormat = ResponseFormat.JSON
    content: ResponseContent = ResponseContent.FULL
    view: ResponseView = ResponseView.DEFAULT
    model: Type[T_ResponseModel] = None

    @model_validator(mode="after")
    def validate_config(self, __context):
        if (
            self.content not in ALLOWABLE_VIEW_RESPONSE_CONTENTS
            and self.view != ResponseView.DEFAULT
        ):
            raise RequestValidationError(
                f"Can only generate a `{str(self.view)}` `view` of query result for `{','.join(ALLOWABLE_VIEW_RESPONSE_CONTENTS)}` response content (see `content`)"
            )

        if self.content != ResponseContent.FULL and self.format in [
            ResponseFormat.VCF,
            ResponseFormat.BED,
        ]:

            raise RequestValidationError(
                f"Can only generate a `{self.format}` response for a `FULL` data query (see `content`)"
            )

        return self

    # from https://stackoverflow.com/a/67366461
    # allows ensurance that model is always a child of ResponseModel
    @field_validator("model")
    def validate_model(cls, model):
        if issubclass(model, ResponseModel):
            return model
        raise RuntimeError(
            f"Wrong type for `model` : `{model}`; must be subclass of `ResponseModel`"
        )

    @field_validator("content")
    def validate_content(cls, content):
        try:
            return ResponseContent(content)
        except NameError:
            raise RequestValidationError(
                f"Invalid value provided for `content`: {content}"
            )

    @field_validator("format")
    def validate_foramt(cls, format):
        try:
            return ResponseFormat(format)
        except NameError:
            raise RequestValidationError(
                f"Invalid value provided for `format`: {format}"
            )

    @field_validator("view")
    def validate_view(cls, view):
        try:
            return ResponseView(view)
        except NameError:
            raise RequestValidationError(f"Invalid value provided for `view`: {format}")
