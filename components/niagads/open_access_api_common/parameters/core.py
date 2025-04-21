from typing import Self
from niagads.enums.core import EnumParameter


class CustomizableEnumParameter(EnumParameter):
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
