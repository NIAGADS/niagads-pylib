from niagads.api.common.models.domain.parameters.types import (
    EnumParameter,
    ResponseContent,
    ResponseFormat,
)


class DefaultRContentParam(EnumParameter):
    """enum for allowable response types"""

    FULL = ResponseContent.FULL.value
    BRIEF = ResponseContent.BRIEF.value
    URLS = ResponseContent.URLS.value
    COUNTS = ResponseContent.COUNTS.value
    IDS = ResponseContent.IDS.value

    @classmethod
    def description(cls):
        message = "Response content (Full response or selected data summaries).  "
        return message + f"{super().description()}"

    @classmethod
    def validate(cls, value):
        return super().validate(value, ResponseContent)


class RContentParamNoCounts(EnumParameter):
    """enum for allowable response types"""

    FULL = ResponseContent.FULL.value
    BRIEF = ResponseContent.BRIEF.value
    URLS = ResponseContent.URLS.value
    IDS = ResponseContent.IDS.value

    @classmethod
    def description(cls):
        message = "Response content (full vs selected subset)"
        return message + f"{super().description()}"

    @classmethod
    def validate(cls, value):
        return super().validate(value, ResponseContent)


class RContentData(EnumParameter):
    """enum for allowable response types"""

    FULL = ResponseContent.FULL.value
    COUNTS = ResponseContent.COUNTS.value

    @classmethod
    def description(cls):
        message = "Response content (full or counts only)"
        return message + f"{super().description()}"

    @classmethod
    def validate(cls, value):
        return super().validate(value, ResponseContent)


class DefaultRFormatParam(EnumParameter):
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
