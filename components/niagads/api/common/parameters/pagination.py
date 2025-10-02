from fastapi import Query
from niagads.exceptions.core import ValidationError
from niagads.api.common.constants import MAX_NUM_PAGES
from niagads.utils.string import is_integer
from pyparsing import Optional


async def page_param(
    page: int = Query(
        default=1,
        description="specify which page of the response to return, if response is paginated",
    )
):
    if is_integer(page) and page > 0 and page <= MAX_NUM_PAGES:
        return page
    else:
        raise ValidationError(
            f"Invalid value specified for `page`: {page}."
            f"Pages should be positive integers in the range [1, {MAX_NUM_PAGES}]"
        )


async def limit_param(
    limit: int = Query(
        default=None,
        description="return as most `limit` number of records or search results",
        gt=0,
    )
):
    return limit
