from typing import Any, Dict

from fastapi import Response
from niagads.api.common.constants import DEFAULT_PAGE_SIZE
from niagads.api.common.models.domain.parameters.internal import (
    InternalRequestParameters,
)
from niagads.api.common.models.domain.parameters.response import (
    ResponseContent,
    ResponseFormat,
    ResponseView,
)
from niagads.api.common.models.response.base import BaseResponseModel
from niagads.api.common.models.response.views.table import TableViewResponse
from niagads.api.common.services.features import FeatureQueryService
from niagads.api.common.services.pagination import PaginationService
from niagads.common.genomic.features.models import GenomicFeature
from niagads.exceptions.core import ValidationError
from pydantic import BaseModel, ConfigDict, field_validator, model_validator

_INTERNAL_PARAMETERS = ["span", "_tracks"]
_ALLOWABLE_VIEW_RESPONSE_CONTENTS = [ResponseContent.FULL, ResponseContent.BRIEF]


class ResponseConfiguration(BaseModel, arbitrary_types_allowed=True):
    """Captures response-related parameter values (format, content, view) and model"""

    format: ResponseFormat = ResponseFormat.JSON
    content: ResponseContent = ResponseContent.FULL
    view: ResponseView = ResponseView.DEFAULT
    model: BaseResponseModel = None

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
        if issubclass(model, BaseResponseModel):
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


class RequestParameters(BaseModel):
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


class EndpointService:

    def __init__(
        self,
        managers: InternalRequestParameters,
        response_config: ResponseConfiguration,
        params: RequestParameters,
        page_size: int = DEFAULT_PAGE_SIZE,
    ):
        self._managers: InternalRequestParameters = managers
        self._response_config: ResponseConfiguration = response_config
        self._parameters: RequestParameters = params
        self._pagination_service = PaginationService(params, page_size=page_size)

    @property
    def pagination(self):
        return self._pagination_service.pagination

    @property
    def page_size(self):
        return self._pagination_service.page_size

    @property
    def result_size(self):
        return self._pagination_service.result_size

    def set_result_size(self, result_size: int):
        self._pagination_service.set_result_size(result_size)

    async def generate_table_response(self, response: BaseResponseModel):
        cache_key, view_response = await self._managers.cache_service.get_view_response(
            ResponseView.TABLE
        )

        if view_response:
            return view_response

        self._managers.request_data.set_request_id(cache_key)

        view_response = TableViewResponse(
            table=response.to_table(id=cache_key),
            request=self._managers.request_data,
            pagination=response.pagination,
        )

        await self._managers.cache_service.set_view_response(
            ResponseView.TABLE, view_response
        )

        return view_response

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

            # cache the response
            await self._managers.cache_service.set_response(response)

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
                    case _:  # JSON
                        return response

            case _:  # IGV_BROWSER
                raise NotImplementedError(
                    f"A response for view of type {str(self._response_config.view)} is coming soon."
                )

    async def get_feature_location(self, feature: GenomicFeature):
        return await FeatureQueryService(
            self._managers.database_session
        ).get_feature_location(feature)
