from fastapi.exceptions import RequestValidationError
from pydantic import BaseModel, model_validator
from sqlalchemy.ext.asyncio import AsyncSession
from fastapi import Depends, Query
from typing import Optional
from typing_extensions import Self
from enum import Enum

from api.response_models.base_models import RequestDataModel
from api.common.formatters import clean

# TODO: common params: https://fastapi.tiangolo.com/tutorial/dependencies/classes-as-dependencies/

# Query(Query()) nesting has to do w/FAST-API bug for documentation of Depends() params
# see https://github.com/tiangolo/fastapi/issues/4700


class PaginationParameters(BaseModel):
    # limit: Optional[int] = Query(Query(default=None, description="maximum number of results to return; please note that `pagination is not yet implemented`"))
    page: Optional[int] = Query(Query(default=None, description="current page; please note that `pagination is not yet implemented`"))
    queryId: Optional[str] = Query(Query(default=None, description="identifier for query being paged; please note that `pagination is not yet implemented`"))
    
    @model_validator(mode = 'after')
    def check_required(self):
        setCount = sum([True for v in [self.page, self.queryId] if v is not None])
        if (setCount == 1 ):
            raise RequestValidationError('Must specify both `page` and `queryId` to retun paged results')
        
        return self
    
    # TODO: some validator against response size?
        

async def ids_only_param(idsOnly: Optional[bool] = Query(default = False, 
    description="return only the IDS (no annotation or metadata) for matching records")) -> bool:
    return idsOnly

async def counts_only_param(countsOnly: Optional[bool] = Query(default = False,
    description="return count of matching records")) -> bool:
    return countsOnly

async def summary_only_param(summary: Optional[bool] = Query(default = False, 
    description="return summary of result; may be a count of matching records or summary table")) -> bool:
    return summary

async def keyword_param(keyword: Optional[str] = Query(default=None, 
    description="search all text fields by keyword")) -> str:
    if keyword is not None:
        return clean(keyword)
    return keyword


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
    
        raise RequestValidationError("Invalid value for `format`: " + value)
    

async def format_param(format: ResponseType = Query(ResponseType.JSON, description="type of response retured by the request")): 
    return ResponseType.validate(clean(format))


