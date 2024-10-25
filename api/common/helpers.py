from sqlalchemy.ext.asyncio import AsyncSession
from pydantic import BaseModel, ConfigDict
from typing import Any, Optional, Dict
from api.dependencies.shared_params import InternalRequestParameters, ResponseType
from api.response_models.base_models import RequestDataModel

class HelperParameters(BaseModel, arbitrary_types_allowed=True):
    internal: InternalRequestParameters
    responseModel: Any
    format: ResponseType = ResponseType.JSON
    parameters: Dict[str, Any]
    
    # __pydantic_extra__: Dict[str, Any]  
    # model_config = ConfigDict(extra='allow')