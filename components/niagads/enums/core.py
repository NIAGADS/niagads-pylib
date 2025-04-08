from math import e
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
        except ValueError as err:
            raise err

    @classmethod
    def has_value(cls, value: str) -> bool:
        """test if the StrEnum contains a value"""
        return value.lower() in [v.lower() for v in cls._value2member_map_]

    def __str__(self):
        return self.value

    @classmethod
    def list(cls) -> bool:
        return [v for v in cls._value2member_map_]
