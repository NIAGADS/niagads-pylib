"""helpers for argparse args, including custom actions"""

import json
from argparse import ArgumentTypeError

from niagads.enums.core import CaseInsensitiveEnum


def json_type(value: str) -> dict:
    """
    convert a JSON string argument value to an object

    Args:
        value (str): JSON string

    Raises:
        argparse.ArgumentTypeError

    Returns:
        dict: decoded JSON
    """
    try:
        return json.decodes(value)
    except:
        raise ArgumentTypeError("Invalid JSON: " + value)


def case_insensitive_enum_type(enumType: CaseInsensitiveEnum):
    """check that the string belongs to the `enumType`"""

    def type_func(value):
        try:
            matchedEnum: CaseInsensitiveEnum = enumType(value)
            return matchedEnum.value

        except:
            raise ArgumentTypeError(
                f"invalid choice: '{value} (choose from [{', '.join(enumType.list())}]"
            )

    return type_func


def comma_separated_list(value: str) -> list:
    """
    Convert a comma-separated string argument value to a list of strings.

    Args:
        value (str): Comma-separated string (e.g., "a,b,c")

    Returns:
        list: List of strings
    Raises:
        argparse.ArgumentTypeError: If no items are provided.
    """
    items = [item.strip() for item in value.split(",") if item.strip()]
    if not items:
        raise ArgumentTypeError(
            "At least one item must be provided (comma-separated list)"
        )
    return items
