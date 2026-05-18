from typing import Optional, Union

from niagads.api.common.constants import DEFAULT_PAGE_SIZE, MAX_NUM_PAGES
from niagads.api.common.models.response.base import PaginationDataModel
from niagads.common.models.types import Range
from niagads.exceptions.core import ValidationError
from pydantic import BaseModel


class PaginationCursor(BaseModel):
    key: Union[str, int]
    offset: Optional[int] = None


class PaginationService:

    def __init__(
        self,
        parameters=None,
        page_size: int = DEFAULT_PAGE_SIZE,
        result_size: Optional[int] = None,
        pagination: Optional[PaginationDataModel] = None,
    ):
        self._parameters = parameters
        self._page_size = page_size
        self._result_size = result_size
        self._pagination = pagination

    @property
    def pagination(self) -> Optional[PaginationDataModel]:
        return self._pagination

    @property
    def page_size(self) -> int:
        return self._page_size

    @property
    def result_size(self) -> Optional[int]:
        return self._result_size

    def set_result_size(self, result_size: Optional[int]):
        self._result_size = result_size

    def page(self):
        if self._parameters is not None:
            return self._parameters.get("page", 1)
        return 1

    def pagination_exists(self, raise_error: bool = True):
        if self._pagination is None:
            if raise_error:
                raise RuntimeError(
                    "Attempting to modify or access pagination before initializing"
                )
            return False
        return True

    def validate_page(self, page: int):
        self.pagination_exists()

        if self._pagination.total_num_pages is None:
            raise RuntimeError(
                "Attempting fetch a page before estimating total number of pages"
            )

        if page > self._pagination.total_num_pages:
            raise ValidationError(
                f"Request `page` {page} does not exist; this query generates a maximum of "
                f"{self._pagination.total_num_pages} pages"
            )

        return True

    def total_num_pages(self):
        if self._result_size is None:
            raise RuntimeError("Attempting to page before estimating result size.")

        if self._result_size > self._page_size * MAX_NUM_PAGES:
            raise ValidationError(
                f"Result size ({self._result_size}) is too large; filter for fewer tracks "
                "or narrow the queried genomic region."
            )

        return (
            1
            if self._result_size < self._page_size
            else next(
                (
                    p
                    for p in range(1, MAX_NUM_PAGES)
                    if (p - 1) * self._page_size > self._result_size
                )
            )
            - 1
        )

    def initialize_pagination(self):
        self._pagination = PaginationDataModel(
            page=self.page(),
            total_num_pages=self.total_num_pages(),
            paged_num_records=None,
            total_num_records=self._result_size,
        )

        return self.validate_page(self._pagination.page)

    def set_paged_num_records(self, num_records: int):
        self.pagination_exists()
        self._pagination.paged_num_records = num_records

    def offset(self):
        self.pagination_exists()
        return (
            None
            if self._pagination.page == 1
            else (self._pagination.page - 1) * self._page_size
        )

    def slice_result_by_page(self, page: int = None) -> Range:
        self.pagination_exists()
        target_page = self._pagination.page if page is None else page
        start = (target_page - 1) * self._page_size
        end = start + self._page_size
        if end > self._result_size:
            end = self._result_size

        return Range(start=start, end=end)
