from typing import Type
from fastapi.exceptions import RequestValidationError


from niagads.open_access_api_common.models.responses.core import (
    ResponseModel,
    T_ResponseModel,
)
from niagads.open_access_api_common.parameters.response import (
    ResponseContent,
    ResponseFormat,
    ResponseView,
)
from pydantic import BaseModel, field_validator, model_validator

ALLOWABLE_VIEW_RESPONSE_CONTENTS = [ResponseContent.FULL, ResponseContent.SUMMARY]


class ResponseConfiguration(BaseModel, arbitrary_types_allowed=True):
    """Captures response-related parameter values (format, content, view) and model"""

    format: ResponseFormat = ResponseFormat.JSON
    content: ResponseContent = ResponseContent.FULL
    view: ResponseView = ResponseView.DEFAULT
    model: Type[T_ResponseModel] = None

    @model_validator(mode="after")
    def validate_config(self, __context):
        if (
            self.content not in ALLOWABLE_VIEW_RESPONSE_CONTENTS
            and self.view != ResponseView.DEFAULT
        ):
            raise RequestValidationError(
                f"Can only generate a `{str(self.view)}` `view` of query result for "
                f"`{','.join(ALLOWABLE_VIEW_RESPONSE_CONTENTS)}` response content (see `content`)"
            )

        if self.content != ResponseContent.FULL and self.format in [
            ResponseFormat.VCF,
            ResponseFormat.BED,
        ]:

            raise RequestValidationError(
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
            raise RequestValidationError(
                f"Invalid value provided for `content`: {content}"
            )

    @field_validator("format")
    def validate_foramt(cls, format):
        try:
            return ResponseFormat(format)
        except NameError:
            raise RequestValidationError(
                f"Invalid value provided for `format`: {format}"
            )

    @field_validator("view")
    def validate_view(cls, view):
        try:
            return ResponseView(view)
        except NameError:
            raise RequestValidationError(f"Invalid value provided for `view`: {format}")
