from typing import Union

from fastapi import APIRouter, Depends
from niagads.api_common.constants import SharedOpenAPITags
from niagads.api_common.models.response.core import RecordResponse
from niagads.open_access_filer_api.dependencies import (
    InternalRequestParameters,
    TextSearchFilterFields,
)
from niagads.open_access_filer_api.documentation import BASE_TAGS

router = APIRouter(prefix="/dictionary", tags=BASE_TAGS)

tags = [str(SharedOpenAPITags.ONTOLOGIES)]


@router.get(
    "/filters",
    tags=tags,
    response_model=Union[RecordResponse],
    summary="get-text-search-filter-fields",
    description="List allowable fields for text search filter expressions.",
)
async def get_allowable_text_filters(
    internal: InternalRequestParameters = Depends(),
) -> RecordResponse:

    return RecordResponse(
        data=TextSearchFilterFields.list(toLower=True), request=internal.request_data
    )


# TODO values for each filter field
"""
@router.get(
    "/filters/{field}",
    tags=tags,
    response_model=Union[RecordResponse],
    summary="get-text-search-filter-fields",
    description="List allowable fields for text search filter expressions.",
)
async def get_allowable_text_filters(
    internal: InternalRequestParameters = Depends(),
) -> RecordResponse:

    return RecordResponse(
        data=TextSearchFilterFields.list(toLower=True), request=internal.requestData
    )
"""
