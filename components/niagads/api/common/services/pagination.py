from typing import Optional, Union

from niagads.api.common.constants import DEFAULT_PAGE_SIZE, MAX_NUM_PAGES
from niagads.api.common.models.responses.pagination import PaginationState
from niagads.common.models.types import Range
from pydantic import BaseModel


class PaginationCursor(BaseModel):
    """Identifies a position within a paginated result."""

    key: Union[str, int]
    offset: Optional[int] = None


class PaginationService:
    """Track pagination state and calculate page boundaries for results."""

    def __init__(
        self,
        result_size: int,
        page: int = 1,
        page_size: int = DEFAULT_PAGE_SIZE,
    ):
        """Initialize the pagination service.

        Args:
            page_size: Maximum number of records returned per page.
        """
        self._result_size: int = result_size
        self._page_size: int = page_size
        self._max_page = self.max_page()

        if self.is_valid_page(page):
            self._page: int = page

    def get_pagination_state(self):
        return PaginationState(
            page=self._page,
            total_pages=self._max_page,
            paged_records=self.paged_records(),
            total_records=self._result_size,
        )

    def paged_records(self):
        """Record the number of records returned for the current page.

        Returns:
            Number of records expected on the current page.
        """
        return max(0, min(self._page_size, self._result_size - self.offset()))

    def is_valid_page(self, page: int):
        """Validate that a page falls within the available page range.

        Args:
            page: One-based page number to validate.

        Returns:
            ``True`` when the page is valid.

        Raises:
            ValueError: If the page exceeds the total number of pages.
            RuntimeError: If pagination has not been initialized.
        """

        if self._max_page is None:
            raise RuntimeError(
                "Attempting fetch a page before estimating total number of pages"
            )

        if page > self._max_page:
            raise ValueError(
                f"Request `page` {page} does not exist; this query generates a maximum "
                f"of {self._max_page} pages"
            )

        return True

    def max_page(self):
        """Calculate the maximum number of pages for a result set.

        Args:
            result_size: Total number of records in the result set.

        Returns:
            The total number of pages.

        Raises:
            RuntimeError: If ``result_size`` is not provided.
            ValueError: If the result exceeds the maximum page limit.
        """
        if self._result_size is None:
            raise RuntimeError("Attempting to page before estimating result size.")

        if self._result_size > self._page_size * MAX_NUM_PAGES:
            raise ValueError(
                f"Result size ({self._result_size}) is too large; please add additional filters or narrow the queried genomic region."
            )

        return max(
            1,
            (self._result_size + self._page_size - 1) // self._page_size,
        )

    def slice_result(self, page: int = None) -> Range:
        """Calculate slice boundaries for a page of an in-memory result.

        Args:
            page: Optional one-based page number. Uses the initialized page
                when omitted.

        Returns:
            A ``Range`` containing the zero-based start index and exclusive end
            index for the requested page.

        Raises:
            ValueError: If an explicitly supplied page is invalid.
            RuntimeError: If pagination has not been initialized.
        """

        if page is not None:
            self.is_valid_page(page)

        target_page = self._page if page is None else page
        start = (target_page - 1) * self._page_size
        # don't subtract 1 from end b/c python slices are not end-range inclusive
        end = start + self._page_size
        if end > self._result_size:
            end = self._result_size

        return Range(start=start, end=end)

    def offset(self):
        """Calculate the zero-based offset for the initialized page.

        Returns:
            The zero-based record offset for the current page.
        """
        return (self._page - 1) * self._page_size
