from enum import auto
from typing import Self, Type

from niagads.enums.core import CaseInsensitiveEnum
from niagads.exceptions.core import ValidationError


class ResponseView(CaseInsensitiveEnum):
    """enum for allowable response views"""

    FULL = auto()
    SUMMARY = auto()
    URLS = auto()
    COUNTS = auto()
    IDS = auto()


class ResponseFormat(CaseInsensitiveEnum):
    """enum for allowable response / output formats"""

    JSON = auto()
    TEXT = auto()


class ResponseLayout(CaseInsensitiveEnum):
    TABLE = auto()
    IGV_CONFIG = auto()
    IGV_TRACK_SELECTOR = auto()
    CHART = auto()
    DEFAULT = auto()


class EnumParameter(CaseInsensitiveEnum):
    """Enum that includes a validator for use as a parameter"""

    @classmethod
    def description(cls):
        return f"Allowable values are: {','.join(cls.list(return_enum_names=False))}."

    @classmethod
    def validate(cls, value, enum_type: Type[CaseInsensitiveEnum]):
        from niagads.api.common.utils import sanitize  # avoid circular import

        try:
            return enum_type(sanitize(value))
        except Exception as err:
            raise ValidationError(f"Invalid value: {cls.description()}")
