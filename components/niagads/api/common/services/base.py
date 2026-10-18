import logging
from typing import Any

from niagads.api.common.models.context.request import Parameters
from niagads.api.common.models.context.response import ResponseConfiguration
from niagads.api.common.models.responses.base import BaseResponseModel
from niagads.api.common.parameters.internal import EndpointContext
from niagads.api.common.services.pagination import PaginationService
from niagads.common.core import ComponentBaseMixin
from niagads.common.models.types import Range


class BaseEndpointService(ComponentBaseMixin):
    _orm_model = None

    def __init__(
        self,
        context: EndpointContext,
        parameters: Parameters,
        response_config: ResponseConfiguration,
    ):
        logger = logging.getLogger(f"uvicorn.error.{self.__class__.__module__}")
        super().__init__(logger=logger)

        self._context: EndpointContext = context
        self._parameters: Parameters = parameters
        self._pagination_service: PaginationService = None
        self._response_config: ResponseConfiguration = response_config

    def __validate_orm_utility(self, function_name: str):
        if not getattr(self._orm_model, function_name, None):
            raise RuntimeError(
                f"`{function_name}` not implemented for {self._orm_model.__name__}"
            )

    async def _fetch_record(self, filters: dict):
        """try and fetch specific record. may occassionally return multiple
        e.g., gene symbols"""
        self.__validate_orm_utility("fetch_record")
        return await self._orm_model.fetch_record(
            self._context.database_session, filters, allow_multiple=True
        )

    async def _lookup_records(self, lookup_value: Any):
        self.__validate_orm_utility("retrieve_records")
        return await self._orm_model.retrieve_records(
            self._context.database_session,
            lookup_value,
        )

    def _initialize_pagination_service(self, result_size):
        """Initialize pagination service
        Developer note: override this in child classes if using a non-standard pagination model
        """
        page = getattr(self._parameters, "page", 1)
        self._pagination_service = PaginationService(result_size=result_size, page=page)

    async def get_cached_response(self):
        """Check for and return a cached result

        Returns:
            The requested response, or None
        """
        # check based on all paramaters
        cache_key = self._context.cache_key.encrypt()
        response = await self._context.cache_manager.get(
            cache_key, namespace=self._context.cache_key.namespace
        )

        return response

    async def generate_response(self, result: Any, from_cache: bool = True):
        """Build a response model and cache it when it is newly generated.

        Args:
            result: Result data, or an existing response when ``from_cache`` is true.
            from_cache: Whether ``result`` is already a response model from the cache.

        Returns:
            The response model.
        """

        # NOTE: temporarily keeping from_cache b/c might need it for format and ui

        if from_cache:
            return result

        self._context.request_data.update_parameters(self._parameters)

        response_model = self._response_config.response_model
        if self._response_config.record_model:
            response_model = response_model[self._response_config.record_model]

        result_size = len(result)
        self._initialize_pagination_service(result_size)
        if self._pagination_service.requires_pagination():
            page_range: Range = self._pagination_service.page_range()
            if isinstance(result, list):
                paged_result = result[page_range.start : page_range.end]
            elif isinstance(result, dict):
                {
                    k: result[k]
                    for k in list(result.keys)[page_range.start : page_range.end]
                }
        else:
            paged_result = result

        response = response_model(
            request=self._context.request_data,
            pagination=self._pagination_service.get_pagination_state(),
            data=paged_result,
        )

        # JSON serializer need b/c of generics
        await self._context.cache_manager.set(
            self._context.cache_key.encrypt(),
            paged_result,
            namespace=self._context.cache_key.namespace,
        )

        return response
