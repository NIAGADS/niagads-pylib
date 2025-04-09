from typing import List, Self
from fastapi.exceptions import RequestValidationError
from niagads.enums.core import CaseInsensitiveEnum
from niagads.string_utils.core import sanitize


class EnumParameter(CaseInsensitiveEnum):
    """Parameter defined by an enum that allows dynamic exclusion of some enum members."""

    @classmethod
    def exclude(cls: Self, name: str, exclude: list):
        """Selective exclude members from the enum

        Args:
            cls (Self)
            name (str): name for the enum subset
            exclude (list): list of enum members to exclude from the subset enum

        Returns:
            EnumParameter: new enum generated from the included (kept) members
        """
        return EnumParameter(
            name, {member.name: member.value for member in cls if member not in exclude}
        )

    @classmethod
    def get_description(cls):
        return f"Allowable values are: {','.join(cls.list())}."

    @classmethod
    def validate(cls, value, label: str, returnCls: CaseInsensitiveEnum):
        try:
            cls(sanitize(value))
            return returnCls(value)
        except:
            raise RequestValidationError(
                f"Invalid value provided for `{label}`: {value}.  {cls.get_description()}"
            )
