from typing import Any, Dict, Optional, Type, Union

from fastapi import Response
from niagads.api.common.constants import DEFAULT_PAGE_SIZE, MAX_NUM_PAGES
from niagads.api.common.models.context.request import Parameters
from niagads.api.common.models.context.response import ResponseConfiguration
from niagads.api.common.models.layouts.table import TableLayoutResponse
from niagads.api.common.models.responses.base import BaseResponseModel
from niagads.api.common.models.responses.pagination import PaginationState
from niagads.api.common.parameters.internal import InternalRequestParameters
from niagads.api.common.parameters.types import (
    ResponseFormat,
    ResponseLayout,
    ResponseView,
)
from niagads.api.common.services.features import FeatureQueryService
from niagads.common.genomic.features.models import GenomicFeature
from niagads.common.models.types import Range
from niagads.exceptions.core import ValidationError
from pydantic import BaseModel
from sqlalchemy import CacheKey

_INTERNAL_PARAMETERS = ["span", "_tracks"]


class PaginationCursor(BaseModel):
    """pagination cursor"""

    key: Union[str, int]
    offset: Optional[int] = None


class EndpointService:

    def __init__(
        self,
        managers: InternalRequestParameters,
        response_config: ResponseConfiguration,
        params: RequestParameters,
        pagination_service: Type[PaginationService],
    ):
        self._managers: InternalRequestParameters = managers
        self._response_config: ResponseConfiguration = response_config
        self._parameters: RequestParameters = params
        self._pagination_service = pagination_service
        self._messages: list[Union[str, dict]] = []

    @property
    def messages(self):
        return self._messages

    @property
    def pagination(self):
        return self._pagination_service.pagination

    @property
    def page_size(self):
        return self._pagination_service.page_size

    @property
    def result_size(self):
        return self._pagination_service.result_size

    def add_message(self, message: Union[str, dict]):
        self._messages.append(message)

    def set_result_size(self, result_size: int):
        self._pagination_service.set_result_size(result_size)

    async def generate_table_response(self, response: BaseResponseModel):
        pass
        # cache_key, view_response = await self._managers.cache_service.get_view_response(
        #     ResponseView.TABLE
        # )

        # if view_response:
        #     return view_response

        # self._managers.request_data.set_request_id(cache_key)

        # view_response = TableViewResponse(
        #     table=response.to_table(id=cache_key),
        #     request=self._managers.request_data,
        #     pagination=response.pagination,
        # )

        # await self._managers.cache_service.set_view_response(
        #     ResponseView.TABLE, view_response
        # )

        # return view_response

    async def get_feature_location(self, feature: GenomicFeature):
        return await FeatureQueryService(
            self._managers.database_session
        ).get_feature_location(feature)


class PaginationService: ...


class RouteHelperService:

    def __init__(
        self,
        managers: InternalRequestParameters,
        responseConfig: ResponseConfiguration,
        params: Parameters,
    ):
        self._managers: InternalRequestParameters = managers
        self._response_config: ResponseConfiguration = responseConfig
        self._pagination: PaginationState = None
        self._parameters: Parameters = params
        self._pageSize: int = DEFAULT_PAGE_SIZE
        self._result_size: int = None

    def set_page_size(self, pageSize: int):
        self._pageSize = pageSize

    async def _get_cached_response(self):
        cache_key = self._managers.cache_key.encrypt()
        response = await self._managers.cache.get(
            cache_key, namespace=self._managers.cache_key.namespace
        )

        if response is not None:
            return await self.generate_response(response, is_cached=True)

        return None

    def _pagination_exists(self, raiseError: bool = True):
        if self._pagination is None:
            if raiseError:
                raise RuntimeError(
                    "Attempting to modify or access pagination before initializing"
                )
            else:
                return False
        return True

    def _is_valid_page(self, page: int):
        """test if the page is valid (w/in range of expected number of pages)"""

        self._pagination_exists()

        if self._pagination.total_num_pages is None:
            raise RuntimeError(
                "Attempting fetch a page before estimating total number of pages"
            )

        if page > self._pagination.total_num_pages:
            raise ValidationError(
                f"Request `page` {page} does not exist; this query generates a maximum of {self._pagination.total_num_pages} pages"
            )

        return True

    def page(self):
        if self._parameters is not None:
            return self._parameters.get("page", 1)
        return 1

    def total_num_pages(self):
        if self._result_size is None:
            raise RuntimeError("Attempting to page before estimating result size.")

        if self._result_size > self._pageSize * MAX_NUM_PAGES:
            raise ValidationError(
                f"Result size ({self._result_size}) is too large; filter for fewer tracks or narrow the queried genomic region."
            )

        return (
            1
            if self._result_size < self._pageSize
            else next(
                (
                    p
                    for p in range(1, MAX_NUM_PAGES)
                    if (p - 1) * self._pageSize > self._result_size
                )
            )
            - 1
        )

    def initialize_pagination(self):
        self._pagination = PaginationState(
            page=self.page(),
            total_num_pages=self.total_num_pages(),
            paged_num_records=None,
            total_num_records=self._result_size,
        )

        return self._is_valid_page(self._pagination.page)

    def set_paged_num_records(self, numRecords: int):
        self._pagination_exists()
        self._pagination.paged_num_records = numRecords

    def offset(self):
        """calculate offset for SQL pagination"""
        self._pagination_exists()
        return (
            None
            if self._pagination.page == 1
            else (self._pagination.page - 1) * self._pageSize
        )

    def slice_result_by_page(self, page: int = None) -> Range:
        """calculates start and end indexes for paging an array"""
        self._pagination_exists()
        targetPage = self._pagination.page if page is None else page
        start = (targetPage - 1) * self._pageSize
        end = (
            start + self._pageSize
        )  # don't subtract 1 b/c python slices are not end-range inclusive
        if end > self._result_size:
            end = self._result_size

        return Range(start=start, end=end)

    async def generate_response(self, result: Any, is_cached: bool = False):
        response: BaseResponseModel = result if is_cached else None
        if response is None:
            self._managers.request_data.update_parameters(
                self._parameters, exclude=_INTERNAL_PARAMETERS
            )

            # set pagination for lists of results
            if isinstance(result, list):
                if not self._pagination_service.pagination_exists(raise_error=False):
                    if self.result_size is None:
                        self.set_result_size(len(result))

                    self._pagination_service.initialize_pagination()

                self._pagination_service.set_paged_num_records(len(result))

                response = self._response_config.model(
                    request=self._managers.request_data,
                    pagination=self.pagination,
                    data=result,
                )
            else:
                # FIXME
                # if self._response_config.model == IGVBrowserTrackSelectorResponse:
                #    queryId = self._managers.cache_service.cache_key.encrypt()
                #    collectionId = self._parameters.get("collection")

                #    response = self._response_config.model(
                #       request=self._managers.request_data,
                #        data=IGVBrowserTrackSelectorResponse.build_table(
                #            result, queryId if collectionId is None else collectionId
                #        ),
                #    )
                # else:
                response = self._response_config.model(
                    request=self._managers.request_data,
                    data=result,  # self._sqa_row2dict(result),
                )

            if len(self._messages) > 0:
                response.message = self._messages
                # FIXME: ? potentially reset messages here? is there anycase where same service generates multiple responses?

            # cache the response
            await self._managers.cache_service.set_response(response)
        return response

        # match self._response_config.view:
        # case ResponseView.TABLE:
        #    return await self.generate_table_response(response)

    async def get_feature_location(self, feature: GenomicFeature):
        return await FeatureQueryService(self._managers.session).get_feature_location(
            feature
        )
