from enum import auto
from typing import Any, Dict, Optional, Type, Union

from fastapi.exceptions import RequestValidationError
from niagads.enums.core import CaseInsensitiveEnum
from niagads.open_access_api_enums.core import CustomizableEnumParameter
from pydantic import BaseModel, ConfigDict, field_validator, model_validator


class ResponseContent(CustomizableEnumParameter):
    """enum for allowable response types"""

    FULL = auto()
    COUNTS = auto()
    IDS = auto()
    SUMMARY = auto()
    URLS = auto()

    @classmethod
    def get_description(cls, inclValues=True):
        message = "Type of information returned by the query."
        return message + f" {super().get_description()}" if inclValues else message

    @classmethod
    def descriptive(cls, inclUrls=False, description=False):
        """return descriptive formats only (usually for metadata)"""
        exclude = (
            [ResponseContent.IDS, ResponseContent.COUNTS]
            if inclUrls
            else [ResponseContent.IDS, ResponseContent.URLS, ResponseContent.COUNTS]
        )
        subset = cls.exclude("descriptive_only_content", exclude)
        if description:
            return cls.get_description(False) + " " + subset.get_description()
        else:
            return subset

    @classmethod
    def data(cls, description=False):
        """return data formats only"""
        subset = cls.exclude(
            "data_only_content", [ResponseContent.IDS, ResponseContent.URLS]
        )
        if description:
            return cls.get_description(False) + " " + subset.get_description()
        else:
            return subset

    @classmethod
    def full_data(cls, description=False):
        """return full data formats only"""
        subset = cls.exclude(
            "full_data_only_content",
            [ResponseContent.IDS, ResponseContent.URLS, ResponseContent.SUMMARY],
        )
        if description:
            return cls.get_description(False) + " " + subset.get_description()
        else:
            return subset


class ResponseFormat(CustomizableEnumParameter):
    """enum for allowable response / output formats"""

    JSON = auto()
    TEXT = auto()
    VCF = auto()
    BED = auto()

    @classmethod
    def get_description(cls, inclValues=True):
        message = "Response format.  If a non-text `view` is specified, the response format will default to `JSON`"
        return message + f" {super().get_description()}" if inclValues else message

    @classmethod
    def generic(cls, description=False):
        subset = cls.exclude(
            "generic_formats", [ResponseFormat.VCF, ResponseFormat.BED]
        )
        if description:
            return cls.get_description(False) + " " + subset.get_description()
        else:
            return subset

    @classmethod
    def functional_genomics(cls, description=False):
        subset = cls.exclude("functional_genomics_formats", [ResponseFormat.VCF])
        if description:
            return cls.get_description(False) + " " + subset.get_description()
        else:
            return subset

    @classmethod
    def variant_score(cls, description=False):
        subset = cls.exclude("variant_score_formats", [ResponseFormat.BED])
        if description:
            return cls.get_description(False) + " " + subset.get_description()
        else:
            return subset


class ResponseView(CustomizableEnumParameter):
    """enum for allowable views"""

    TABLE = auto()
    IGV_BROWSER = auto()
    DEFAULT = auto()

    @classmethod
    def get_description(cls, inclValues=True):
        message = "Visual representation of the data.  Select `DEFAULT` for TEXT or JSON response."
        return message + f" {super().get_description()}" if inclValues else message

    @classmethod
    def table(cls, description=False):
        subset = cls.exclude("table_views", [ResponseView.IGV_BROWSER])
        if description:
            return cls.get_description(False) + " " + subset.get_description()
        else:
            return subset


# FIXME: is this really necessary? onRowSelect can be driven by the target view
class OnRowSelect(CaseInsensitiveEnum):
    """enum for allowable NIAGADS-viz-js/Table onRowSelect actions"""

    ACCESS_ROW_DATA = auto()
    UPDATE_GENOME_BROWSER = auto()
    UPDATE_LOCUSZOOM = auto()


_ALLOWABLE_VIEW_RESPONSE_CONTENTS = [ResponseContent.FULL, ResponseContent.SUMMARY]


class ResponseConfiguration(BaseModel, arbitrary_types_allowed=True):
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
            raise RequestValidationError(
                f"Can only generate a `{str(self.view)}` `view` of query result for `{','.join(_ALLOWABLE_VIEW_RESPONSE_CONTENTS)}` response content (see `content`)"
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
    # allows ensurance that model is always a child of BaseResponseModel
    @field_validator("model")
    def validate_model(cls, model):
        if issubclass(model, BaseResponseModel):
            return model
        raise RuntimeError(
            f"Wrong type for `model` : `{model}`; must be subclass of `BaseResponseModel`"
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
