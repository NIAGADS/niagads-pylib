from typing import Annotated, Literal

from fastapi import Query
from pydantic import BeforeValidator

from niagads.api.common.parameters.validators import sanitize_enum_value
from niagads.api.common.types import ResponseFormat, ResponseContent


async def response_content_param(
    view: Annotated[
        ResponseContent,
        BeforeValidator(sanitize_enum_value(ResponseContent)),
        Query(description="TBD"),
    ] = ResponseContent.FULL,
) -> ResponseContent:
    return view


async def data_response_content_param(
    view: Annotated[
        Literal[ResponseContent.FULL, ResponseContent.COUNTS],
        BeforeValidator(sanitize_enum_value(ResponseContent)),
        Query(description="help message TBD"),
    ] = ResponseContent.FULL,
) -> ResponseContent:
    return view


async def response_format_param(
    format: Annotated[
        ResponseFormat,
        BeforeValidator(sanitize_enum_value(ResponseFormat)),
        Query(description="TBD"),
    ] = ResponseFormat.JSON,
) -> ResponseFormat:
    return format


# allowable response views for single record lookups
async def record_response_format_param(
    format: Annotated[
        ResponseFormat,
        BeforeValidator(sanitize_enum_value(ResponseFormat)),
        Query(description="TBD"),
    ] = ResponseFormat.JSON,
) -> ResponseFormat:
    return format
