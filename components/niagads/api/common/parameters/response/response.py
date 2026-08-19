from typing import Annotated, Literal

from fastapi import Query
from pydantic import BeforeValidator

from components.niagads.api.common.parameters.validators import generate_enum_sanitizer
from components.niagads.api.common.types import ResponseFormat, ResponseView

RESPONSE_VIEW_QUERY_PARAM = Annotated[
    ResponseView,
    BeforeValidator(generate_enum_sanitizer(ResponseView)),
    Query(default=ResponseView.FULL, description="TBD"),
]

DATA_RESPONSE_VIEW_QUERY_PARAM = Annotated[
    Literal[ResponseView.FULL, ResponseView.COUNTS],
    BeforeValidator(generate_enum_sanitizer(ResponseView)),
    Query(default=ResponseView.FULL, description="help message TBD"),
]


RESPONSE_FORMAT_QUERY_PARAM = Annotated[
    ResponseFormat,
    BeforeValidator(generate_enum_sanitizer(ResponseFormat)),
    Query(default=ResponseFormat.JSON, description="TBD"),
]
