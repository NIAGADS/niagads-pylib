from fastapi import Query
from fastapi.exceptions import RequestValidationError
from niagads.open_access_api_common.config.constants import MAX_NUM_PAGES
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
        raise RequestValidationError(
            f"Invalid value specified for `page`: {page}."
            f"Pages should be positive integers in the range [1, {MAX_NUM_PAGES}]"
        )
