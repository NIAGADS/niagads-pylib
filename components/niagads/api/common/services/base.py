from typing import Any

from niagads.api.common.models.context.request import Parameters
from niagads.api.common.models.context.response import ResponseConfiguration
from niagads.api.common.models.responses.base import BaseResponseModel
from niagads.api.common.parameters.internal import EndpointContext
from niagads.common.models.types import Range

from components.niagads.api.common.services.pagination import PaginationService


class BaseEndpointService:
    _orm_model = None

    def __init__(
        self,
        context: EndpointContext,
        parameters: Parameters,
        response_config: ResponseConfiguration,
    ):
        self._context: EndpointContext = context
        self._parameters: Parameters = parameters
        self._pagination_service: PaginationService = None
        self._response_config: ResponseConfiguration = response_config

    def __validate_orm_utility(self, orm_model, function_name: str):
        if not getattr(self._orm_model, function_name, None):
            raise RuntimeError(
                f"`{function_name}` not implemented for {self._orm_model.__name__}"
            )

    async def _lookup_records(self, lookup_value: Any):
        self.__validate_orm_utility("fetch_record")
        return await self._orm_model.fetch_record(
            self._context.database_session, lookup_value
        )

    async def _initialize_pagination_service(self, result_size):
        """Initialize pagination service
        Developer note: override this in child classes if using a non-standard pagination model
        """
        page = getattr(self._parameters, "page", 1)
        self._pagination_service = PaginationService(result_size=result_size, page=1)

    async def _get_cached_response(self):
        cache_key = self._context.cache_key.encrypt()
        response = await self._context.cache_manager.get(
            cache_key, namespace=self._context.cache_key.namespace
        )

        if response is not None:
            return await self.generate_response(response, is_cached=True)

        return None

    async def generate_response(
        self, result: Any, *, is_paged: bool = False, is_cached: bool = False
    ):
        """Build a response model and cache it when it is newly generated.

        Args:
            result: Result data, or an existing response when ``is_cached`` is true.
            is_paged: Whether the result is already paginated
            is_cached: Whether ``result`` is already a response model from the cache.

        Returns:
            The response model.
        """
        response: type[BaseResponseModel] = result if is_cached else None
        if response is None:
            self._context.request_data.update_parameters(self._parameters)

            response_model = self._response_config.response_model
            if self._response_config.record_model:
                response_model = response_model[self._response_config.record_model]

            if isinstance(result, list) and not is_paged:
                page_range: Range = self._pagination_service.page_range()
                paged_result = result[page_range.start : page_range.end]

            response = response_model(
                request=self._context.request_data,
                pagination=self._pagination_service.get_pagination_state(),
                data=result if is_paged else paged_result,
            )

            await self._context.cache_manager.set(
                self._context.cache_key.encrypt(),
                response,
                namespace=self._context.cache_key.namespace,
            )
        return response
