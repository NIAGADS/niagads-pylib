from pydantic import BaseModel, model_validator
from sqlalchemy.ext.asyncio import AsyncSession
from fastapi import Depends, Query
from typing import Optional
from typing_extensions import Self
from enum import Enum

from api.response_models.base_models import RequestDataModel

from .param_validation import clean

# TODO: common params: https://fastapi.tiangolo.com/tutorial/dependencies/classes-as-dependencies/

# Query(Query()) nesting has to do w/FAST-API bug for documentation of Depends() params
# see https://github.com/tiangolo/fastapi/issues/4700

class OptionalParams(BaseModel):
    limit: Optional[int] = Query(Query(default=None, description="maximum number of results to return; please note that `pagination is not yet implemented`"))
    page: Optional[int] = Query(Query(default=None, description="current page; please note that `pagination is not yet implemented`"))
    countOnly: Optional[bool] = Query(Query(default = False, description="return result size (count) only"))

class ExtendedOptionalParams(OptionalParams):
    idsOnly: Optional[bool] = Query(Query(default = False, description="return only the IDS (no annotation or metadata) for matching records"))

class InternalRequestParameters(BaseModel, arbitrary_types_allowed=True):
    requestData: RequestDataModel = Depends(RequestDataModel.from_request)
    session: AsyncSession

# FIXME: use internal model_validation instead of class method
class ResponseType(str, Enum):
    """ enum for allowable response / output types"""
    JSON = "json"
    TABLE = "table"
    # XML = "xml"
        
    @classmethod
    def validate(self, value: str): # allow to be case insensitive
        for e in self:
            if e.value.lower() == value.lower(): 
                return e.value
    
        raise ValueError("Invalid response `format`: " + value)
    


async def format_param(format: ResponseType = Query(ResponseType.JSON, description="type of response retured by the request")): 
    return ResponseType.validate(clean(format))


