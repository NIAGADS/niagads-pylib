from enum import auto
from typing import Self, Type

from pydantic import BaseModel

from niagads.enums.core import CaseInsensitiveEnum
from niagads.exceptions.core import ValidationError


class EnumParameter(BaseModel):
    """Enum that includes a validator for use as a parameter"""

    @classmethod
    def description(cls, enum_type: Type[CaseInsensitiveEnum]):
        return f"Allowable values are: {','.join(enum_type.list(return_enum_names=False))}."

    @classmethod
    def validate(cls, value, enum_type: Type[CaseInsensitiveEnum]):
        from niagads.api.common.utils import sanitize  # avoid circular import

        try:
            return enum_type(sanitize(value))
        except Exception as err:
            raise ValidationError(f"Invalid value: {cls.description()}")
