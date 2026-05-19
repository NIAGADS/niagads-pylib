from typing import Self

from niagads.enums.core import CaseInsensitiveEnum
from niagads.exceptions.core import ValidationError


class EnumParameter(CaseInsensitiveEnum):
    """Enum that includes a validator for use as a parameter"""

    @classmethod
    def description(cls):
        return f"Allowable values are: {','.join(cls.list(return_enum_names=False))}."

    @classmethod
    def label(cls):
        raise NotImplementedError(
            "This method needs to be overridden in child EnumParameters"
        )

    @classmethod
    def validate(cls, value):
        from niagads.api.common.utils import sanitize  # avoid circular import

        try:
            return cls(sanitize(value))
        except Exception as err:
            raise ValidationError(
                f"Invalid value provided for `{cls.label}`: {value}.  {cls.description()}"
            )

    @classmethod
    def subset(cls: Self, names: list[str]) -> Self:
        """Create a subset enum with only the specified member names.

        Args:
            cls (Self): the enum class
            names (list[str]): list of enum member names to include in subset

        Returns:
            EnumParameter: new enum generated from the included members
        """
        subset_members = {
            member.name: member.value for member in cls if member.name in names
        }
        return EnumParameter(cls.__name__, subset_members)
