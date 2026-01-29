from sys import version_info
from typing import List

if version_info >= (3.11,):
    from enum import StrEnum
else:
    from strenum import StrEnum


class CaseInsensitiveEnum(StrEnum):
    """
    extension for a `StrEnum` that allows for case insensitivity on the values
    StrEnum (from strenum)'s auto function matches the case of the Enum item name
        e.g.,   UPPPER_CASE = auto() -> UPPPER_CASE
                lower_case = auto() -> lower_case
                Mixed_Case = auto() -> Mixed_Case

    overriding _missing_ to return a case insensitve match
    """

    # after from https://stackoverflow.com/a/76131490
    @classmethod
    def _missing_(cls, value: str):  # allow to be case insensitive
        try:
            for member in cls:
                if member.value.lower() == value.lower():
                    return member
                if member.name.lower() == value.lower():
                    return member
        except ValueError as err:
            raise err

    @classmethod
    def has_value(cls, value: str) -> bool:
        """test if the StrEnum contains a value"""
        return value.lower() in [v.lower() for v in cls._value2member_map_]

    def __str__(self):
        return self.value

    @classmethod
    def list(cls, to_lower: bool = False, return_enum_names: bool = False) -> List[str]:
        values = (
            [member.name for member in cls]
            if return_enum_names
            else [member.value for member in cls]
        )

        if to_lower:
            return [v.lower() for v in values]
        else:
            return values
