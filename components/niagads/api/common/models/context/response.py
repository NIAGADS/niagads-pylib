from typing import Any, Optional

from niagads.api.common.models.records.types import RecordT
from niagads.api.common.models.responses.base import BaseResponseModel
from niagads.api.common.types import (
    ResponseContent,
    ResponseFormat,
    ResponseUI,
)
from pydantic import BaseModel, field_validator, model_validator


class ResponseConfiguration(BaseModel, arbitrary_types_allowed=True):
    """Captures parameter values (format, content, view) and model needed to build the response"""

    format: Optional[ResponseFormat] = ResponseFormat.JSON
    content: Optional[ResponseContent] = ResponseContent.FULL
    ui_component: Optional[ResponseUI] = ResponseUI.DEFAULT
    record_model: type[RecordT]
    response_model: type[BaseResponseModel]

    # from https://stackoverflow.com/a/67366461
    # allows ensurance that model is always a child
    @field_validator("response_model")
    def validate_model(cls, model):
        if issubclass(model, BaseResponseModel):
            return model
        raise RuntimeError(
            f"Wrong type for `model` : `{model}`; must be a subclass of `BaseResponseModel`"
        )

    @field_validator("ui_component")
    def validate_ui(cls, ui):
        try:
            return ResponseUI(ui)
        except NameError:
            raise ValueError(f"Invalid value provided for `ui`: {ui}")

    @field_validator("format")
    def validate_format(cls, format):
        try:
            return ResponseFormat(format)
        except NameError:
            raise ValueError(f"Invalid value provided for `format`: {format}")

    @field_validator("content")
    def validate_view(cls, content):
        try:
            return ResponseContent(content)
        except NameError:
            raise ValueError(f"Invalid value provided for `content`: {content}")
