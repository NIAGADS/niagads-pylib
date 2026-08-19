from components.niagads.api.common.utils import sanitize
from components.niagads.enums.core import CaseInsensitiveEnum


def parse_list_parameter(value_str: str) -> list[str]:
    if any(delim in value_str for delim in [":", "|", ";", " ", "\t", "/", "\\"]):
        raise ValueError(
            "Invalid delimiter; please separate multiple identifiers with commas (`,`)."
        )
    return value_str.split(",")


def sanitize_value(value: str) -> str:
    if isinstance(value, str):
        return sanitize(value)
    return value


def generate_enum_sanitizer(enum_type: type[CaseInsensitiveEnum]):

    def sanitizer(value: str):
        try:
            return enum_type(value)  # Uses the extra parameter dynamically
        except:
            raise ValueError(f"{value} is not a valid `{enum_type.__name__}`")

    return sanitizer
