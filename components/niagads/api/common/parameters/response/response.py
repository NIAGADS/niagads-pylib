from typing import Annotated, Literal

from fastapi import Query
from pydantic import BeforeValidator

from niagads.api.common.parameters.validators import sanitize_enum_value
from niagads.api.common.types import ResponseFormat, ResponseView


async def response_view_param(
    view: Annotated[
        ResponseView,
        BeforeValidator(sanitize_enum_value(ResponseView)),
        Query(description="TBD"),
    ] = ResponseView.FULL,
) -> ResponseView:
    return view


async def data_response_view_param(
    view: Annotated[
        Literal[ResponseView.FULL, ResponseView.COUNTS],
        BeforeValidator(sanitize_enum_value(ResponseView)),
        Query(description="help message TBD"),
    ] = ResponseView.FULL,
) -> ResponseView:
    return view


async def response_format_param(
    format: Annotated[
        ResponseFormat,
        BeforeValidator(sanitize_enum_value(ResponseFormat)),
        Query(description="TBD"),
    ] = ResponseFormat.JSON,
) -> ResponseFormat:
    return format
