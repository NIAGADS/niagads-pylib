from typing import Any, Dict, Optional, Type, Union

from fastapi import Response
from niagads.api_common.models.features.genomic import GenomicFeature
from niagads.common.models.structures import Range
from niagads.exceptions.core import ValidationError
from niagads.api_common.constants import DEFAULT_PAGE_SIZE, MAX_NUM_PAGES
from niagads.api_common.models.response.core import (
    AbstractResponse,
    T_RecordResponse,
    T_Response,
)
from niagads.api_common.models.response.pagination import (
    PaginationDataModel,
)
from niagads.api_common.models.services.cache import (
    CacheKeyDataModel,
    CacheKeyQualifier,
    CacheNamespace,
)
from niagads.api_common.models.datasets.igvbrowser import (
    IGVBrowserTrackSelectorResponse,
)
from niagads.api_common.parameters.internal import InternalRequestParameters
from niagads.api_common.parameters.response import (
    ResponseContent,
    ResponseFormat,
    ResponseView,
)
from niagads.api_common.services.features import FeatureQueryService
from niagads.api_common.views.table import TableViewResponse
from pydantic import BaseModel, ConfigDict, field_validator, model_validator

_INTERNAL_PARAMETERS = ["span", "_tracks"]
_ALLOWABLE_VIEW_RESPONSE_CONTENTS = [ResponseContent.FULL, ResponseContent.BRIEF]


class ResponseConfiguration(BaseModel, arbitrary_types_allowed=True):
    """Captures response-related parameter values (format, content, view) and model"""

    format: ResponseFormat = ResponseFormat.JSON
    content: ResponseContent = ResponseContent.FULL
    view: ResponseView = ResponseView.DEFAULT
    model: Type[T_Response] = None

    @model_validator(mode="after")
    def validate_config(self, __context):
        if (
            self.content not in _ALLOWABLE_VIEW_RESPONSE_CONTENTS
            and self.view != ResponseView.DEFAULT
        ):
            raise ValidationError(
                f"Can only generate a `{str(self.view)}` `view` of query result for "
                f"`{','.join(_ALLOWABLE_VIEW_RESPONSE_CONTENTS)}` response content (see `content`)"
            )

        if self.content != ResponseContent.FULL and self.format in [
            ResponseFormat.VCF,
            ResponseFormat.BED,
        ]:

            raise ValidationError(
                f"Can only generate a `{self.format}` response for a `FULL` data query (see `content`)"
            )

        return self

    # from https://stackoverflow.com/a/67366461
    # allows ensurance that model is always a child of RecordResponse
    @field_validator("model")
    def validate_model(cls, model):
        if issubclass(model, AbstractResponse):
            return model
        raise RuntimeError(
            f"Wrong type for `model` : `{model}`; must be subclass of `AbstractResponse`"
        )

    @field_validator("content")
    def validate_content(cls, content):
        try:
            return ResponseContent(content)
        except NameError:
            raise ValidationError(f"Invalid value provided for `content`: {content}")

    @field_validator("format")
    def validate_foramt(cls, format):
        try:
            return ResponseFormat(format)
        except NameError:
            raise ValidationError(f"Invalid value provided for `format`: {format}")

    @field_validator("view")
    def validate_view(cls, view):
        try:
            return ResponseView(view)
        except NameError:
            raise ValidationError(f"Invalid value provided for `view`: {format}")


class PaginationCursor(BaseModel):
    """pagination cursor"""

    key: Union[str, int]
    offset: Optional[int] = None


class Parameters(BaseModel):
    """arbitrary namespace to store request parameters and pass them to helpers"""

    __pydantic_extra__: Dict[str, Any]
    model_config = ConfigDict(extra="allow")

    def get(self, attribute: str, default: Any = None):
        if attribute in self.model_extra:
            return self.model_extra[attribute]
        else:
            return default

    def update(self, attribute: str, value: Any):
        self.model_extra[attribute] = value


class RouteHelperService:

    def __init__(
        self,
        managers: InternalRequestParameters,
        responseConfig: ResponseConfiguration,
        params: Parameters,
    ):
        self._managers: InternalRequestParameters = managers
        self._response_config: ResponseConfiguration = responseConfig
        self._pagination: PaginationDataModel = None
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
        self._pagination = PaginationDataModel(
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

    async def generate_table_response(self, response: Type[T_RecordResponse]):
        # create an encrypted cache key
        cache_key = CacheKeyDataModel.encrypt_key(
            self._managers.cache_key.key
            + str(CacheKeyQualifier.VIEW)
            + str(ResponseView.TABLE)
        )

        viewResponse = await self._managers.cache.get(
            cache_key, namespace=CacheNamespace.VIEW
        )

        if viewResponse:
            return viewResponse

        self._managers.request_data.set_request_id(cache_key)

        viewResponse = TableViewResponse(
            table=response.to_table(id=cache_key),
            request=self._managers.request_data,
            pagination=response.pagination,
        )

        await self._managers.cache.set(
            cache_key, viewResponse, namespace=CacheNamespace.VIEW
        )

        return viewResponse

    async def generate_response(self, result: Any, is_cached: bool = False):
        response: Type[T_RecordResponse] = result if is_cached else None
        if response is None:
            self._managers.request_data.update_parameters(
                self._parameters, exclude=_INTERNAL_PARAMETERS
            )

            # set pagination for lists of results
            if isinstance(result, list):
                if not self._pagination_exists(raiseError=False):
                    if self._result_size is None:
                        self._result_size = len(result)

                    self.initialize_pagination()

                self.set_paged_num_records(len(result))

                response = self._response_config.model(
                    request=self._managers.request_data,
                    pagination=self._pagination,
                    data=result,
                )
            else:
                if self._response_config.model == IGVBrowserTrackSelectorResponse:
                    queryId = self._managers.cache_key.encrypt()
                    collectionId = self._parameters.get("collection")

                    response = self._response_config.model(
                        request=self._managers.request_data,
                        data=IGVBrowserTrackSelectorResponse.build_table(
                            result, queryId if collectionId is None else collectionId
                        ),
                    )
                else:
                    response = self._response_config.model(
                        request=self._managers.request_data,
                        data=result,  # self._sqa_row2dict(result),
                    )

            # cache the response
            await self._managers.cache.set(
                self._managers.cache_key.encrypt(),
                response,
                namespace=self._managers.cache_key.namespace,
            )

        match self._response_config.view:
            case ResponseView.TABLE:
                return await self.generate_table_response(response)

            case ResponseView.DEFAULT:
                match self._response_config.format:
                    case ResponseFormat.TEXT:
                        return Response(
                            response.to_text(incl_header=True),
                            media_type="text/plain",
                        )
                    case ResponseFormat.BED:
                        return Response(
                            response.to_bed(),
                            media_type="text/plain",
                        )
                    case ResponseFormat.VCF:
                        return Response(
                            response.to_vcf(),
                            media_type="text/plain",
                        )
                    case _:  # JSON
                        return response

            case _:  # IGV_BROWSER
                raise NotImplementedError(
                    f"A response for view of type {str(self._response_config.view)} is coming soon."
                )

    async def get_feature_location(self, feature: GenomicFeature):
        return await FeatureQueryService(self._managers.session).get_feature_location(
            feature
        )
