import logging
from collections import Counter
from typing import Any, Union

from niagads.api.common.models.annotations.associations import VariantAssociation
from niagads.api.common.models.context.request import Parameters
from niagads.api.common.models.context.response import ResponseConfiguration
from niagads.api.common.models.records.types import DynamicRecord
from niagads.api.common.models.responses.base import BaseResponseModel
from niagads.api.common.parameters.internal import EndpointContext
from niagads.api.common.services.pagination import PaginationService
from niagads.common.core import ComponentBaseMixin
from niagads.common.models.types import Range
from niagads.common.types import RecordRetrievalResult
from niagads.common.variant.models.record import VariantRecord
from niagads.database.genomicsdb.schema.dataset.track import Track
from niagads.database.genomicsdb.schema.results.associations import (
    VariantAssociation as VAOrm,
)
from niagads.utils.regular_expressions import RegularExpressions
from niagads.utils.string import matches


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

    async def generate_response(self, result: Any, from_cache: bool = False):
        """Build a response model and cache it when it is newly generated.

        Args:
            result: Result data, or an existing response when ``from_cache`` is true.
            from_cache: Whether ``result`` is already a response model from the cache.

        Returns:
            The response model.
        """

        # NOTE: temporarily keeping from_cache b/c might need it for format and ui
        response_model = self._response_config.response_model
        if self._response_config.record_model:
            response_model = response_model[self._response_config.record_model]

        if from_cache:  # use cached data & pagination state
            paged_result = result["data"]
            pagination_state = result["pagination"]
        else:
            self._context.request_data.update_parameters(self._parameters)
            self._initialize_pagination_service(len(result))

            if self._pagination_service.requires_pagination():
                page_range: Range = self._pagination_service.page_range()
                if isinstance(result, list):
                    paged_result = result[page_range.start : page_range.end]
                elif isinstance(result, dict):
                    paged_result = {
                        k: result[k]
                        for k in list(result.keys())[page_range.start : page_range.end]
                    }
            else:
                paged_result = result

            pagination_state = self._pagination_service.get_pagination_state()

        await self._context.cache_manager.set(
            self._context.cache_key.encrypt(),
            {"data": paged_result, "pagination": pagination_state},
            namespace=self._context.cache_key.namespace,
        )

        return response_model(
            request=self._context.request_data,
            pagination=pagination_state,
            data=paged_result,
        )

    async def _generate_association_lookup_result(
        self, associations: list[dict], *, summary: bool = False
    ) -> Union[list[VariantAssociation], list[DynamicRecord]]:
        """Assemble variant associations with their track phenotypes.

        Args:
            associations (list[dict]): retrieved variant associations

        Returns:
            Union[list[VariantAssociation], list[DynamicRecord]]: Associations
                with track phenotypes, or per-track traits and association
                counts. Returns an empty list if no associations are found.
        """

        if not associations:
            return []

        track_stable_ids = [a.get("track_stable_id") for a in associations]
        track_mappings = await Track.retrieve_records(
            self._context.database_session, track_stable_ids
        )
        track_traits = {}
        for track_stable_id, tracks in track_mappings.items():
            phenotypes = tracks[0]["participant_phenotypes"]
            track_traits[track_stable_id] = (
                {key: value for key, value in phenotypes.items() if value is not None}
                if phenotypes is not None
                else None
            )

        if summary:
            return [
                DynamicRecord(
                    track=track_id,
                    traits=track_traits[track_id],
                    num_associations=count,
                )
                for track_id, count in Counter(track_stable_ids).items()
            ]

        results = []
        for assoc in associations:
            variant_id = assoc["variant_stable_id"]
            is_structural_variant = matches(
                variant_id, RegularExpressions.STRUCTUAL_VARIANT_ID
            )
            track_id = assoc["track_stable_id"]

            if is_structural_variant:
                variant_association = VariantAssociation(
                    **assoc,
                    variant=variant_id,
                    traits=track_traits[track_id],
                    track=track_id,
                )

            else:
                variant: VariantRecord = VariantRecord.from_positional_id(variant_id)
                variant_association = VariantAssociation(
                    **assoc,
                    variant=variant_id,
                    ref=variant.ref,
                    alt=variant.alt,
                    traits=track_traits[track_id],
                    track=track_id,
                )

            results.append(variant_association)
        return results
