from niagads.exceptions.core import ValidationError


def parse_list_parameter(value_str: str) -> list[str]:
    if any(delim in value_str for delim in [":", "|", ";", " ", "\t", "/", "\\"]):
        raise ValidationError(
            "Invalid delimiter; please separate multiple identifiers with commas (`,`)."
        )
    return value_str.split(",")
