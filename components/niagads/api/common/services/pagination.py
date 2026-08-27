from abc import ABC, abstractmethod
from typing import List, Optional, Union

from niagads.api.common.constants import DEFAULT_PAGE_SIZE, MAX_NUM_PAGES
from niagads.api.common.models.domain.entities.dataset.track import TrackResultMetrics
from niagads.api.common.models.domain.entities.features.bed import BEDFeature
from niagads.api.common.models.service.cache import (
    CacheKeyDataModel,
    CacheKeyQualifier,
    CacheNamespace,
)
from niagads.api.common.models.response.base import PaginationDataModel
from niagads.api.common.services.cache import CacheService
from niagads.common.models.types import Range
from niagads.exceptions.core import ValidationError
from niagads.utils.list import cumulative_sum
from pydantic import BaseModel


class PaginationCursor(BaseModel):
    key: Union[str, int]
    offset: Optional[int] = None


class TrackDataPaginationCursor(BaseModel):
    tracks: List[str]
    start: PaginationCursor
    end: PaginationCursor


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


class TrackDataPaginationService(PaginationService, ABC):

    def __init__(
        self,
        parameters,
        cache_service: CacheService,
        page_size: int = DEFAULT_PAGE_SIZE,
    ):
        super().__init__(parameters, page_size=page_size)
        self._cache_service = cache_service

    async def build_page_cursor(
        self, track_result_summary: List[TrackResultMetrics]
    ) -> TrackDataPaginationCursor:
        sorted_track_result_summary: List[TrackResultMetrics] = TrackResultMetrics.sort(
            track_result_summary
        )
        no_page_cache_key = self._cache_service.cache_key.no_page()

        cursor_cache_key = CacheKeyDataModel.encrypt_key(
            no_page_cache_key + CacheKeyQualifier.CURSOR
        )
        result_size_cache_key = CacheKeyDataModel.encrypt_key(
            no_page_cache_key + CacheKeyQualifier.RESULT_SIZE
        )

        cursors = await self._cache_service.get(
            cursor_cache_key,
            namespace=CacheNamespace.QUERY_CACHE,
        )
        self.set_result_size(
            await self._cache_service.get(
                result_size_cache_key,
                namespace=CacheNamespace.QUERY_CACHE,
            )
        )

        if cursors is None or self.result_size is None:
            cumulative_sum_by_track = cumulative_sum(
                [t.count for t in sorted_track_result_summary]
            )
            self.set_result_size(cumulative_sum_by_track[-1])

            await self._cache_service.set(
                result_size_cache_key,
                self.result_size,
                namespace=CacheNamespace.QUERY_CACHE,
            )

            self.initialize_pagination()

            cursors = ["0:0"]
            if self.result_size > self.page_size:
                residual_records = 0
                prior_track_index = 0
                offset = 0
                for page in range(1, self.pagination.total_num_pages):
                    slice_range = self.slice_result_by_page(page)
                    for index, counts in enumerate(cumulative_sum_by_track):
                        if counts > slice_range.end:
                            offset = (
                                offset + self.page_size
                                if prior_track_index == index
                                else self.page_size - residual_records
                            )
                            cursors.append(f"{index}:{offset}")

                            residual_records = (
                                sorted_track_result_summary[index].count - offset
                            )
                            prior_track_index = index
                            break

            cursors.append(
                f"{len(sorted_track_result_summary)-1}:{sorted_track_result_summary[-1].count}"
            )

            await self._cache_service.set(
                cursor_cache_key,
                cursors,
                namespace=CacheNamespace.QUERY_CACHE,
            )
        else:
            self.initialize_pagination()

        start_track_index, start_offset = [
            int(x) for x in cursors[self.pagination.page - 1].split(":")
        ]
        end_track_index, end_index = [
            int(x) for x in cursors[self.pagination.page].split(":")
        ]
        paged_tracks = [
            t.id
            for t in sorted_track_result_summary[
                start_track_index : end_track_index + 1
            ]
        ]

        return TrackDataPaginationCursor(
            tracks=paged_tracks,
            start=PaginationCursor(key=0, offset=start_offset),
            end=PaginationCursor(
                key=end_track_index - start_track_index, offset=end_index
            ),
        )

    @abstractmethod
    def page_data(self, cursor: TrackDataPaginationCursor, data: List) -> List:
        raise NotImplementedError
