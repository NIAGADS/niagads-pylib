from fastapi.exceptions import RequestValidationError
from pydantic import BaseModel, field_validator, ConfigDict
from typing import Any, Dict
from enum import Enum

from api.common.enums import ResponseContent
from api.dependencies.parameters.services import InternalRequestParameters
from api.dependencies.parameters.optional import PaginationParameters, ResponseFormat
from api.response_models.base_models import BaseResponseModel

# basically allow creation of an arbitrary namespace
class Parameters(BaseModel):
    __pydantic_extra__: Dict[str, Any]  
    model_config = ConfigDict(extra='allow')
    
class HelperParameters(BaseModel, arbitrary_types_allowed=True):
    internal: InternalRequestParameters
    model: Any
    format: ResponseFormat = ResponseFormat.JSON
    content: ResponseContent = ResponseContent.FULL
    pagination: PaginationParameters = None
    parameters: Parameters = None
    
    # __pydantic_extra__: Dict[str, Any]  
    # model_config = ConfigDict(extra='allow')
    
    # from https://stackoverflow.com/a/67366461
    # allows ensurance taht model is always a child of BaseResponseModel
    @field_validator("model")
    def validate_model(cls, model):
        if issubclass(model, BaseResponseModel):
            return model
        raise RuntimeError(f'Wrong type for `model` : `{model}`; must be subclass of `BaseResponseModel`')
    
    @field_validator("content")
    def validate_content(cls, content):
        try:
            return ResponseContent(content)
        except NameError:
            raise RequestValidationError(f'Invalid value provided for `content`: {content}')
        

