from typing import Self
from niagads.enums.core import CaseInsensitiveEnum


class EnumParameter(CaseInsensitiveEnum):
    """Enum that includes a validator for use as a parameter"""

    @classmethod
    def get_description(cls):
        return f"Allowable values are: {','.join(cls.list())}."

    @classmethod
    def validate(cls, value, label: str, returnCls: CaseInsensitiveEnum):
        from niagads.exceptions.core import ValidationError
        from niagads.api.common.utils import sanitize  # avoid circular import

        try:
            cls(sanitize(value))
            return returnCls(value)
        except Exception as err:
            raise ValidationError(
                f"Invalid value provided for `{label}`: {value}.  {cls.get_description()}"
            )

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
