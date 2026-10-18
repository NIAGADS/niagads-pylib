from typing import Any, Optional

from niagads.api.common.models.context.request import Parameters
from niagads.api.common.models.context.response import ResponseConfiguration
from niagads.api.common.models.responses.base import BaseResponseModel
from niagads.api.common.parameters.internal import EndpointContext


from components.niagads.api.common.services.pagination import PaginationService


class BaseEndpointService:

    def __init__(
        self,
        context: EndpointContext,
        parameters: Parameters,
        response_config: ResponseConfiguration,
        orm_model: Optional[Any] = None,  # the SQLAlchemy ORM model for queries
    ):
        self._context: EndpointContext = context
        self._parameters: Parameters = parameters
        self._pagination_service: PaginationService = None
        self._orm_model = orm_model

    def __validate_orm_utility(self, orm_model, function_name: str):
        if not getattr(self._orm_model, function_name, None):
            raise RuntimeError(
                f"`{function_name}` not implemented for {self._orm_model.__name__}"
            )

    async def _retrieve_records(self, lookup_value: Any):
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

    async def generate_response(self, result: Any, *, is_cached: bool = False):
        response: type[BaseResponseModel] = result if is_cached else None
        if response is None:
            self._context.request_data.update_parameters(self._parameters)

            response = self._response_config.model(
                request=self._context.request_data,
                pagination=self.pagination,
                data=result,
            )

            await self._context.cache_manager.set(
                self._context.cache_key.encrypt(),
                response,
                namespace=self._context.cache_key.namespace,
            )
        return response
