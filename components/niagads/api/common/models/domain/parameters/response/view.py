from niagads.api.common.models.domain.parameters.types import (
    EnumParameter,
    ResponseFormat,
    ResponseView,
)


class ResponseViewEnumParam(EnumParameter):
    """enum for allowable response types"""

    FULL = ResponseView.FULL.value
    BRIEF = ResponseView.BRIEF.value
    URLS = ResponseView.URLS.value
    COUNTS = ResponseView.COUNTS.value
    IDS = ResponseView.IDS.value

    @classmethod
    def description(cls):
        message = "Response content (Full response or selected data summaries).  "
        return message + f"{super().description()}"

    @classmethod
    def validate(cls, value):
        return super().validate(value, ResponseView)


class DataQueryResponseViewEnumParam(EnumParameter):
    """enum for allowable response types"""

    FULL = ResponseView.FULL.value
    COUNTS = ResponseView.COUNTS.value

    @classmethod
    def description(cls):
        message = "Response content (full or counts only)"
        return message + f"{super().description()}"

    @classmethod
    def validate(cls, value):
        return super().validate(value, ResponseView)


class ResponseFormatEnumParam(EnumParameter):
    """enum for allowable response / output formats"""

    TEXT = ResponseFormat.TEXT.value
    JSON = ResponseFormat.JSON.value

    @classmethod
    def description(cls):
        message = "Response format."
        return message + f" {super().description()}"

    @classmethod
    def validate(cls, value):
        return super().validate(value, ResponseFormat)
