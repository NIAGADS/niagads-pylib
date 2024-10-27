from fastapi.exceptions import RequestValidationError, ResponseValidationError
from pydantic import BaseModel, model_validator
from sqlalchemy.ext.asyncio import AsyncSession
from fastapi import Depends, Query
from typing import Optional
from typing_extensions import Self
from enum import Enum

from api.common.enums import ResponseFormat, ResponseType
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

async def summary_only_param(summaryOnly: Optional[bool] = Query(default = False, 
    description="return a brief summary of the result (e.g., simplified metadata with matching record counts)")) -> bool:
    return summaryOnly

async def keyword_param(keyword: Optional[str] = Query(default=None, 
    description="search all text fields by keyword")) -> str:
    if keyword is not None:
        return clean(keyword)
    return keyword

async def format_param(format: ResponseFormat = Query(ResponseFormat.JSON, description="format of response retured by the request")): 
    try:
        return ResponseFormat(clean(format))
    except:
        raise ResponseValidationError(f'Invalid value provided for `format`: {format}')


