"""Validation helpers for shared API parameters."""

from components.niagads.api.common.utils import sanitize
from components.niagads.enums.core import CaseInsensitiveEnum


def parse_comma_separated_list(value_str: str) -> list[str]:
    """Parse a comma-separated string into a list of values.

    Args:
        value_str: Comma-separated string to parse.

    Returns:
        The values from `value_str` split on commas.

    Raises:
        ValueError: If the string contains an unsupported delimiter.
    """
    if any(delim in value_str for delim in [":", "|", ";", " ", "\t", "/", "\\"]):
        raise ValueError(
            "Invalid delimiter; please separate multiple identifiers with commas (`,`)."
        )
    return value_str.split(",")


def sanitize_value(value: str) -> str:
    """Sanitize a string value for use as an API parameter.

    Args:
        value: Value to sanitize.

    Returns:
        The sanitized string value.
    """
    if isinstance(value, str):
        return sanitize(value)
    return value


def sanitize_enum_value(enum_type: type[CaseInsensitiveEnum]):
    """Create a validator that sanitizes strings before applying enum validation.

    Args:
        enum_type: Case-insensitive enum class used for validation.

    Returns:
        A validator that converts a string to a member of `enum_type`.
    """

    def sanitizer(value: str):
        """Convert a string to a member of the configured enum.

        Args:
            value: String value to validate and convert.

        Returns:
            The matching member of `enum_type`.

        Raises:
            ValueError: If `value` is not a valid enum value.
        """
        try:
            return enum_type(sanitize_value(value))
        except:
            raise ValueError(f"{value} is not a valid `{enum_type.__name__}`")

    return sanitizer
