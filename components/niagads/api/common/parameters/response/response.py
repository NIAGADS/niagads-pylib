from typing import Annotated, Literal

from fastapi import Query
from niagads.api.common.parameters.validators import sanitize_enum_value
from niagads.api.common.types import ResponseContent, ResponseFormat
from pydantic import BeforeValidator


async def record_response_content_param(
    content: Annotated[
        Literal[ResponseContent.FULL, ResponseContent.SUMMARY, ResponseContent.IDS],
        BeforeValidator(sanitize_enum_value(ResponseContent)),
        Query(
            description=(
                "Select the type of content included in the response: "
                "comprehensive report, summary report, or identifiers."
            )
        ),
    ] = ResponseContent.FULL,
) -> ResponseContent:
    return content


async def response_content_param(
    content: Annotated[
        ResponseContent,
        BeforeValidator(sanitize_enum_value(ResponseContent)),
        Query(
            description=(
                "Select the type of content included in the response: "
                "comprehensive report, a summary report, resource URLs, counts, or identifiers."
            )
        ),
    ] = ResponseContent.FULL,
) -> ResponseContent:
    return content


async def data_response_content_param(
    content: Annotated[
        Literal[ResponseContent.FULL, ResponseContent.SUMMARY],
        BeforeValidator(sanitize_enum_value(ResponseContent)),
        Query(
            description=(
                "Select whether the response includes the full data or only the "
                "a summary report (categorized counts)."
            )
        ),
    ] = ResponseContent.FULL,
) -> ResponseContent:
    return content


async def response_format_param(
    format: Annotated[
        ResponseFormat,
        BeforeValidator(sanitize_enum_value(ResponseFormat)),
        Query(description="Select the response format: JSON, text, or XML."),
    ] = ResponseFormat.JSON,
) -> ResponseFormat:
    return format


# allowable response contents for single record lookups
async def record_response_format_param(
    format: Annotated[
        Literal[ResponseFormat.JSON, ResponseFormat.XML],
        BeforeValidator(sanitize_enum_value(ResponseFormat)),
        Query(description="Select the record response format: JSON or XML."),
    ] = ResponseFormat.JSON,
) -> ResponseFormat:
    return format
