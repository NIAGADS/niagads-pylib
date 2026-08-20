from typing import Any

from niagads.api.common.models.context.request import Parameters
from niagads.api.common.models.context.response import ResponseConfiguration
from niagads.api.common.models.responses.base import BaseResponseModel
from niagads.api.common.models.responses.pagination import PaginationState
from niagads.api.common.parameters.internal import EndpointContext
from niagads.api.common.services.features import FeatureQueryService
from niagads.common.genomic.features.models import GenomicFeature

from components.niagads.api.common.services.pagination import PaginationService

# FIXME: revise handling of these
_INTERNAL_PARAMETERS = ["span", "_tracks"]

# TODO: figure out how best to handle pagination service and where to instantiate


class EndpointService:

    def __init__(
        self,
        context: EndpointContext,
        parameters: Parameters,
        response_config: ResponseConfiguration,
        pagination_service: type[PaginationService],
    ):
        self._context: EndpointContext = context

        self._parameters: Parameters = parameters
        # initialize pagination service
        self._pagination_service = pagination_service

    async def get_cached_response(self):
        cache_key = self._context.cache_key.encrypt()
        response = await self._context.cache_manager.get(
            cache_key, namespace=self._context.cache_key.namespace
        )

        if response is not None:
            return await self.generate_response(response, is_cached=True)

        return None

    async def generate_response(self, result: Any, is_cached: bool = False):
        response: BaseResponseModel = result if is_cached else None
        if response is None:
            self._context.request_data.update_parameters(
                self._parameters, exclude=_INTERNAL_PARAMETERS
            )

            # set pagination for lists of results
            if isinstance(result, list):
                result_size = len(result)

                if not self._pagination_service.exists(raise_error=False):
                    if self.result_size is None:
                        self.set_result_size(len(result))

                    self._pagination_service.initialize_pagination()

                self._pagination_service.set_paged_num_records(len(result))

                response = self._response_config.model(
                    request=self._context.request_data,
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
                    request=self._context.request_data,
                    data=result,  # self._sqa_row2dict(result),
                )

            if len(self._messages) > 0:
                response.message = self._messages
                # FIXME: ? potentially reset messages here? is there anycase where same service generates multiple responses?

            # cache the response
            await self._context.cache_service.set_response(response)
        return response

        # match self._response_config.view:
        # case ResponseView.TABLE:
        #    return await self.generate_table_response(response)

    async def get_feature_location(self, feature: GenomicFeature):
        return await FeatureQueryService(self._context.session).get_feature_location(
            feature
        )
