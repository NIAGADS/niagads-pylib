
from fastapi import Query
from typing import  Optional

from fastapi.exceptions import RequestValidationError
from niagads.utils.string import is_integer

from api.common.constants import MAX_NUM_PAGES
from api.common.formatters import clean

# Query(Query()) nesting has to do w/FAST-API bug for documentation of Depends() params
# see https://github.com/tiangolo/fastapi/issues/4700


async def page_param(page:Optional[int]=Query(default=1, description="specify which page of the response to return, if response is paginated")):
    if is_integer(page) and page > 0 and page <= MAX_NUM_PAGES:
        return page
    else:
        raise RequestValidationError(f'Invalid value specified for `page`: {page}.  Pages should be positive integers in the range [1, {MAX_NUM_PAGES}]')


async def keyword_param(keyword: Optional[str] = Query(default=None, 
    description="Search all text annotations by keyword.  Matches are exact and case-sensitive.")) -> str:
    if keyword is not None:
        return clean(keyword)
    return keyword



