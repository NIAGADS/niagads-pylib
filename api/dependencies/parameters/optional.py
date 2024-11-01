from fastapi.exceptions import RequestValidationError, ResponseValidationError
from pydantic import BaseModel, field_validator, model_validator
from sqlalchemy.ext.asyncio import AsyncSession
from fastapi import Depends, Query
from typing import List, Optional
from typing_extensions import Self
from enum import Enum

from api.common.enums import CaseInsensitiveEnum, ResponseFormat, ResponseContent
from api.common.formatters import clean, print_enum_values

# TODO: common params: https://fastapi.tiangolo.com/tutorial/dependencies/classes-as-dependencies/

# Query(Query()) nesting has to do w/FAST-API bug for documentation of Depends() params
# see https://github.com/tiangolo/fastapi/issues/4700


class PaginationParameters(BaseModel):
    # limit: Optional[int] = Query(Query(default=None, description="maximum number of results to return; please note that `pagination is not yet implemented`"))
    page: Optional[int] = Query(Query(default=1, description="specify which page of the response to return, if response is paginated"))
    
    # TODO: queryId in case we allow queries to persist in cache and be later retrieved
    """
    queryId: Optional[str] = Query(Query(default=None, description="identifier for query being paged; please note that `pagination is not yet implemented`"))

    @model_validator(mode = 'after')
    def check_required(self):
        setCount = sum([True for v in [self.page, self.queryId] if v is not None])
        if (setCount == 1 ):
            raise RequestValidationError('Must specify both `page` and `queryId` to retun paged results')
        
        return self
    """

"""
# FIXME: would prefer this approach to handle content but challenge is documentation w/correct list of choices
class ResponseContentParameter(BaseModel):
    __choices: CaseInsensitiveEnum = ResponseContent
    content: ResponseContent 
    
    def __init__(self, exclude: List[ResponseContent], default=ResponseContent.FULL):
        self.__choices = CaseInsensitiveEnum('content', { member.name: member.value for member in ResponseContent if member not in exclude })
        self.content = default
    
    @field_validator('content', mode='after')
    def validate_content(self, value):
        try:
            self.__choices(value)
            self.content = ResponseContent(value)
            return self
        except:
            raise RequestValidationError(f'Invalid value provided for `content`: {value}.  Allowable values for this query are: {print_enum_values(self.__choices)}' )

    def __call__(self):
        return self.content
"""
        
def get_response_content(exclude: List[ResponseContent]):
    return CaseInsensitiveEnum('content', { member.name: member.value for member in ResponseContent if member not in exclude })

async def validate_response_content(contentEnum: CaseInsensitiveEnum, value):
    try:
        contentEnum(value)
        return ResponseContent(value)
    except:
        raise RequestValidationError(f'Invalid value provided for `content`: {value}.  Allowable values for this query are: {print_enum_values(contentEnum)}' )

def get_response_format(exclude: List[ResponseFormat]):
    return CaseInsensitiveEnum('format', { member.name: member.value for member in ResponseFormat if member not in exclude })

async def validate_response_format(formatEnum: CaseInsensitiveEnum, value):
    try:
        formatEnum(value)
        return ResponseFormat(value)
    except:
        raise RequestValidationError(f'Invalid value provided for `format`: {value}.  Allowable values for this query are: {print_enum_values(formatEnum)}' )



async def keyword_param(keyword: Optional[str] = Query(default=None, 
    description="search all text fields by keyword")) -> str:
    if keyword is not None:
        return clean(keyword)
    return keyword

async def format_param(format: ResponseFormat = Query(ResponseFormat.JSON,
    description="format of response retured by the request")): 
    try:
        return ResponseFormat(clean(format))
    except:
        raise ResponseValidationError(f'Invalid value provided for `format`: {format}')


