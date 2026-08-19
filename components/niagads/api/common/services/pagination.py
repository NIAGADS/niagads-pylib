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
        page_size: int = DEFAULT_PAGE_SIZE,
    ):
        """Initialize the pagination service.

        Args:
            page_size: Maximum number of records returned per page.
        """
        self._page_size = page_size
        self._pagination: PaginationState = None

    def initialize(self, page: int, result_size: int):
        """Initialize pagination state for a result set.

        Args:
            page: One-based page number requested by the caller.
            result_size: Total number of records in the result set.

        Returns:
            ``True`` when the requested page is valid.
        """
        self._pagination = PaginationState(
            page=1 if page is None else page,
            total_num_pages=self._calculate_total_num_pages(result_size),
            paged_num_records=None,
            total_num_records=result_size,
        )

        return self.is_valid_page(self._pagination.page)

    def set_paged_num_records(self, num_records: int):
        """Record the number of records returned for the current page.

        Args:
            num_records: Number of records in the current page.
        """
        self.exists()
        self._pagination.paged_num_records = num_records

    def exists(self, raise_error: bool = True):
        """Check whether pagination has been initialized.

        Args:
            raise_error: Whether to raise an error when pagination is absent.

        Returns:
            ``True`` when initialized, otherwise ``False`` when ``raise_error``
            is false.

        Raises:
            RuntimeError: If pagination is absent and ``raise_error`` is true.
        """
        if self._pagination is None:
            if raise_error:
                raise RuntimeError(
                    "Attempting to modify or access pagination before initializing"
                )
            else:
                return False
        return True

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

        self.exists()

        if self._pagination.total_num_pages is None:
            raise RuntimeError(
                "Attempting fetch a page before estimating total number of pages"
            )

        if page > self._pagination.total_num_pages:
            raise ValueError(
                f"Request `page` {page} does not exist; this query generates a maximum "
                f"of {self._pagination.total_num_pages} pages"
            )

        return True

    def _calculate_total_num_pages(self, result_size: int):
        """Calculate the total number of pages for a result set.

        Args:
            result_size: Total number of records in the result set.

        Returns:
            The number of pages, with at least one page for an empty result.

        Raises:
            RuntimeError: If ``result_size`` is not provided.
            ValueError: If the result exceeds the maximum page limit.
        """
        if result_size is None:
            raise RuntimeError("Attempting to page before estimating result size.")

        if result_size > self._page_size * MAX_NUM_PAGES:
            raise ValueError(
                f"Result size ({result_size}) is too large; please add additional filters or narrow the queried genomic region."
            )

        return max(
            1,
            (result_size + self._page_size - 1) // self._page_size,
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
        self.exists()
        if page is not None:
            if self.is_valid_page(page):
                target_page = page
        else:
            target_page = self._pagination.page
        start = (target_page - 1) * self._page_size
        # don't subtract 1 from end b/c python slices are not end-range inclusive
        end = start + self._page_size
        if end > self._pagination.total_num_records:
            end = self._pagination.total_num_records

        return Range(start=start, end=end)

    def offset(self):
        """Calculate the SQL offset for the initialized page.

        Returns:
            ``None`` for the first page; otherwise, the zero-based record
            offset for the current page.

        Raises:
            RuntimeError: If pagination has not been initialized.
        """
        self.exists()
        return (
            None
            if self._pagination.page == 1
            else (self._pagination.page - 1) * self._page_size
        )
