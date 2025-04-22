from typing import Optional
from pydantic import BaseModel, Field


class PaginationDataModel(BaseModel):
    """Captures pagination status."""

    page: int = Field(
        default=1,
        description="if result is paged, indicates the current page of the result; defaults to 1",
    )
    total_num_pages: int = Field(
        default=1,
        description="if the result is paged, reports total number of pages in the full result set (response); defaults to 1",
    )
    paged_num_records: Optional[int] = Field(
        default=None,
        description="number of records in the current paged result set (response)",
    )
    total_num_records: Optional[int] = Field(
        default=None,
        description="total number of records in the full result set (response)",
    )
