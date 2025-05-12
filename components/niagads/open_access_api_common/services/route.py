from typing import Any, Dict, Optional, Type, Union

from fastapi import Response
from niagads.exceptions.core import ValidationError
from niagads.common.models.core import Range
from niagads.open_access_api_common.config.constants import (
    DEFAULT_PAGE_SIZE,
    MAX_NUM_PAGES,
)
from niagads.open_access_api_common.models.cache import (
    CacheKeyDataModel,
    CacheKeyQualifier,
    CacheNamespace,
)
from niagads.open_access_api_common.models.records.core import DynamicRowModel
from niagads.open_access_api_common.models.records.track.igvbrowser import (
    IGVBrowserTrackSelectorResponse,
)
from niagads.open_access_api_common.models.response.core import (
    ResponseModel,
    T_ResponseModel,
)
from niagads.open_access_api_common.models.response.pagination import (
    PaginationDataModel,
)
from niagads.open_access_api_common.models.views.table.core import TableViewResponse
from niagads.open_access_api_common.parameters.internal import InternalRequestParameters
from niagads.open_access_api_common.parameters.response import (
    ResponseContent,
    ResponseFormat,
    ResponseView,
)

from pydantic import BaseModel, ConfigDict, field_validator, model_validator
from sqlalchemy import RowMapping

_INTERNAL_PARAMETERS = ["span", "_tracks"]
_ALLOWABLE_VIEW_RESPONSE_CONTENTS = [ResponseContent.FULL, ResponseContent.SUMMARY]


class ResponseConfiguration(BaseModel, arbitrary_types_allowed=True):
    """Captures response-related parameter values (format, content, view) and model"""

    format: ResponseFormat = ResponseFormat.JSON
    content: ResponseContent = ResponseContent.FULL
    view: ResponseView = ResponseView.DEFAULT
    model: Type[T_ResponseModel] = None

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
    # allows ensurance that model is always a child of ResponseModel
    @field_validator("model")
    def validate_model(cls, model):
        if issubclass(model, ResponseModel):
            return model
        raise RuntimeError(
            f"Wrong type for `model` : `{model}`; must be subclass of `ResponseModel`"
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
        self._responseConfig: ResponseConfiguration = responseConfig
        self._pagination: PaginationDataModel = None
        self._parameters: Parameters = params
        self._pageSize: int = DEFAULT_PAGE_SIZE
        self._resultSize: int = None

    def set_page_size(self, pageSize: int):
        self._pageSize = pageSize

    async def _get_cached_response(self):
        cacheKey = self._managers.cacheKey.encrypt()
        response = await self._managers.cache.get(
            cacheKey, namespace=self._managers.cacheKey.namespace
        )

        if response is not None:
            return await self.generate_response(response, isCached=True)

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
        if self._resultSize is None:
            raise RuntimeError("Attempting to page before estimating result size.")

        if self._resultSize > self._pageSize * MAX_NUM_PAGES:
            raise ValidationError(
                f"Result size ({self._resultSize}) is too large; filter for fewer tracks or narrow the queried genomic region."
            )

        return (
            1
            if self._resultSize < self._pageSize
            else next(
                (
                    p
                    for p in range(1, MAX_NUM_PAGES)
                    if (p - 1) * self._pageSize > self._resultSize
                )
            )
            - 1
        )

    def initialize_pagination(self, raiseError=True):
        """returns False if not a paged model and raiseError = False"""
        if self._responseConfig.model.is_paged():
            self._pagination = PaginationDataModel(
                page=self.page(),
                total_num_pages=self.total_num_pages(),
                paged_num_records=None,
                total_num_records=self._resultSize,
            )

            return self._is_valid_page(self._pagination.page)
        else:
            if raiseError:
                raise RuntimeError("Attempt to page a non-pageable response model")
            return False

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
        if end > self._resultSize:
            end = self._resultSize

        return Range(start=start, end=end)

    async def generate_table_response(self, response: Type[T_ResponseModel]):
        # create an encrypted cache key
        cacheKey = CacheKeyDataModel.encrypt_key(
            self._managers.cacheKey.key
            + str(CacheKeyQualifier.VIEW)
            + str(ResponseView.TABLE)
        )

        viewResponse = await self._managers.cache.get(
            cacheKey, namespace=CacheNamespace.VIEW
        )

        if viewResponse:
            return viewResponse

        self._managers.requestData.set_request_id(cacheKey)

        if self._responseConfig.format != ResponseFormat.JSON:
            self._managers.requestData.add_message(
                f"WARNING: `Table` VIEW requested; response format changed to `{ResponseFormat.JSON.value}`"
            )

        viewResponse = TableViewResponse(
            table=response.to_view(ResponseView.TABLE, id=cacheKey),
            request=self._managers.requestData,
            pagination=response.pagination if response.is_paged() else None,
        )

        await self._managers.cache.set(
            cacheKey, viewResponse, namespace=CacheNamespace.VIEW
        )

        return viewResponse

    async def generate_response(self, result: Any, isCached=False):
        response: Type[T_ResponseModel] = result if isCached else None
        if response is None:
            self._managers.requestData.update_parameters(
                self._parameters, exclude=_INTERNAL_PARAMETERS
            )

            if self._responseConfig.model.is_paged():
                if not self._pagination_exists(raiseError=False):
                    if self._resultSize is None:
                        self._resultSize = len(result)

                    self.initialize_pagination()

                self.set_paged_num_records(len(result))

                response = self._responseConfig.model(
                    request=self._managers.requestData,
                    pagination=self._pagination,
                    data=result,  # self._sqa_row2dict(result),
                )
            else:
                if self._responseConfig.model == IGVBrowserTrackSelectorResponse:
                    queryId = self._managers.cacheKey.encrypt()
                    collectionId = self._parameters.get("collection")

                    response = self._responseConfig.model(
                        request=self._managers.requestData,
                        data=IGVBrowserTrackSelectorResponse.build_table(
                            result, queryId if collectionId is None else collectionId
                        ),
                    )
                else:
                    response = self._responseConfig.model(
                        request=self._managers.requestData,
                        data=result,  # self._sqa_row2dict(result),
                    )

            # cache the response
            await self._managers.cache.set(
                self._managers.cacheKey.encrypt(),
                response,
                namespace=self._managers.cacheKey.namespace,
            )

        match self._responseConfig.view:
            case ResponseView.TABLE:
                return await self.generate_table_response(response)

            case ResponseView.DEFAULT:
                if self._responseConfig.format in [
                    ResponseFormat.TEXT,
                    ResponseFormat.BED,
                    ResponseFormat.VCF,
                ]:
                    try:
                        nullStr = (
                            None
                            if self._responseConfig.format == ResponseFormat.TEXT
                            else "."
                        )
                        return Response(
                            response.to_text(
                                self._responseConfig.format, nullStr=nullStr
                            ),
                            media_type="text/plain",
                        )
                    except NotImplementedError as err:
                        if self._responseConfig.format == ResponseFormat.TEXT:
                            response.add_message(
                                f"{str(err)} Returning default JSON response."
                            )
                            return response
                        else:
                            raise err
                else:  # JSON
                    return response

            case _:  # IGV_BROWSER
                raise NotImplementedError(
                    f"A response for view of type {str(self._responseConfig.view)} is coming soon."
                )
