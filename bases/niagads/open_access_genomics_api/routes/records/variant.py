from typing import Union
from fastapi import APIRouter, Depends, Query
from niagads.open_access_api_common.config.constants import SharedOpenAPITags

from niagads.open_access_api_common.models.features.genomic import GenomicFeature
from niagads.open_access_api_common.models.features.variant import (
    AbridgedVariantResponse,
    VariantResponse,
)
from niagads.open_access_api_common.parameters.record.path import variant_param
from niagads.open_access_api_common.parameters.response import (
    ResponseContent,
    ResponseFormat,
)
from niagads.open_access_api_common.services.route import (
    Parameters,
    ResponseConfiguration,
)
from niagads.open_access_genomics_api.dependencies import InternalRequestParameters
from niagads.open_access_genomics_api.documentation import APP_NAME
from niagads.open_access_genomics_api.queries.variant import VariantRecordQuery
from niagads.open_access_genomics_api.services.route import GenomicsRouteHelper

router = APIRouter(
    prefix="/record/variant",
    tags=[
        APP_NAME,
        str(SharedOpenAPITags.VARIANT_RECORD),
    ],
)


@router.get(
    "/{variant}",
    response_model=Union[AbridgedVariantResponse, VariantResponse],
    name="Get variant record",
    description="retrieve an annotated variant",
)
async def get_variant(
    variant: GenomicFeature = Depends(variant_param),
    content: str = Query(
        ResponseContent.FULL,
        description=ResponseContent.descriptive(description=True),
    ),
    format: str = Query(
        ResponseFormat.JSON, description=ResponseFormat.generic(description=True)
    ),
    internal: InternalRequestParameters = Depends(),
) -> Union[AbridgedVariantResponse, VariantResponse]:

    rContent = ResponseContent.descriptive().validate(
        content, "content", ResponseContent
    )
    rFormat = ResponseFormat.generic().validate(format, "format", ResponseFormat)
    helper = GenomicsRouteHelper(
        internal,
        ResponseConfiguration(
            content=rContent,
            format=rFormat,
            model=(
                VariantResponse
                if rContent == ResponseContent.FULL
                else AbridgedVariantResponse
            ),
        ),
        Parameters(id=variant.feature_id),
        # idParameter="id",
        query=VariantRecordQuery,
    )

    return await helper.get_query_response()
