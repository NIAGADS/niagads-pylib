from typing import Optional

from fastapi import Query
from niagads.api.common.constants import MAX_NUM_PAGES


async def page_param(
    page: int = Query(
        default=1,
        description="One-based page number to return when the response is paginated.",
        gt=0,
        le=MAX_NUM_PAGES,
    )
) -> int:
    return page


async def limit_param(
    limit: Optional[int] = Query(
        default=None,
        description="Maximum number of records or search results to return for the request.",
        gt=0,
    )
) -> Optional[int]:
    return limit
