from niagads.api.common.models.responses.base import BaseResponseModel
from niagads.api.common.parameters.types import (
    ResponseFormat,
    ResponseLayout,
    ResponseView,
)
from niagads.exceptions.core import ValidationError
from pydantic import BaseModel, field_validator, model_validator


class ResponseConfiguration(BaseModel, arbitrary_types_allowed=True):
    """Captures parameter values (format, content, view) and model needed to build the response"""

    format: ResponseFormat = ResponseFormat.JSON
    view: ResponseView = ResponseView.FULL
    layout: ResponseLayout = ResponseLayout.DEFAULT
    model: type[BaseResponseModel] = None

    @model_validator(mode="after")
    def validate_config(self, __context):
        if (
            self.view not in [ResponseView.FULL, ResponseView.SUMMARY]
            and self.layout != ResponseLayout.DEFAULT
        ):
            raise ValidationError(
                f"Can only generate a `{str(self.layout)}` `layout` of the result for "
                f"`full` and `summary` response `views`"
            )

        return self

    # from https://stackoverflow.com/a/67366461
    # allows ensurance that model is always a child
    @field_validator("model")
    def validate_model(cls, model):
        if issubclass(model, BaseResponseModel):
            return model
        raise RuntimeError(
            f"Wrong type for `model` : `{model}`; must be a subclass of `BaseResponseModel`"
        )

    @field_validator("layout")
    def validate_layout(cls, layout):
        try:
            return ResponseLayout(layout)
        except NameError:
            raise ValidationError(f"Invalid value provided for `layout`: {layout}")

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
