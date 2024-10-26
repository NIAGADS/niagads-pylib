
from pydantic import BaseModel, ConfigDict, field_validator
from typing import Any, Optional, Dict
from api.dependencies.shared_params import InternalRequestParameters, ResponseType
from api.response_models.base_models import BaseResponseModel, RequestDataModel

class HelperParameters(BaseModel, arbitrary_types_allowed=True):
    internal: InternalRequestParameters
    model: Any
    format: ResponseType = ResponseType.JSON
    parameters: Dict[str, Any]
    
    # __pydantic_extra__: Dict[str, Any]  
    # model_config = ConfigDict(extra='allow')
    
    # from https://stackoverflow.com/a/67366461
    # allows ensurance taht model is always a child of BaseResponseModel
    @field_validator("model")
    def validate_model(cls, model):
        if issubclass(model, BaseResponseModel):
            return model
        raise RuntimeError(f'Wrong type for `model` : `{model}`; must be subclass of `BaseResponseModel`')
