from typing import Optional

from fastapi import Query
from niagads.api.common.constants import MAX_NUM_PAGES


async def page_param(
    page: int = Query(
        default=1,
        description="specify which page of the response to return, if response is paginated",
        gt=0,
        le=MAX_NUM_PAGES,
    )
) -> int:
    return page


async def limit_param(
    limit: Optional[int] = Query(
        default=None,
        description="return as most `limit` number of records or search results",
        gt=0,
    )
) -> Optional[int]:
    return limit
