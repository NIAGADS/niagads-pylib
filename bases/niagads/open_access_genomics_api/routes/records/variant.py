from typing import Union
from fastapi import APIRouter, Depends, Query
from niagads.open_access_api_common.config.constants import SharedOpenAPITags

from niagads.open_access_api_common.models.features.genomic import GenomicFeature
from niagads.open_access_api_common.models.features.variant import (
    AbridgedVariantResponse,
    VariantAnnotationResponse,
    VariantResponse,
)
from niagads.open_access_api_common.parameters.record.path import variant_param
from niagads.open_access_api_common.parameters.response import (
    ResponseContent,
    ResponseFormat,
    ResponseView,
)
from niagads.open_access_api_common.services.route import (
    Parameters,
    ResponseConfiguration,
)
from niagads.open_access_api_common.views.table import TableViewResponse
from niagads.open_access_genomics_api.dependencies import InternalRequestParameters
from niagads.open_access_genomics_api.documentation import APP_NAME
from niagads.open_access_genomics_api.queries.variant import (
    VariantFrequencyQuery,
    VariantRecordQuery,
)
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


@router.get(
    "/{variant}/frequencies",
    response_model=Union[VariantAnnotationResponse, TableViewResponse],
    name="Get variant allele frequencies",
    description="Get allele frequencies from open-access databases, incl. 1000Genomes, ALFA, ExAC",
)
async def get_variant_allele_frequencies(
    variant: GenomicFeature = Depends(variant_param),
    format: str = Query(
        ResponseFormat.JSON, description=ResponseFormat.generic(description=True)
    ),
    view: str = Query(
        ResponseView.DEFAULT, description=ResponseView.table(description=True)
    ),
    internal: InternalRequestParameters = Depends(),
) -> Union[VariantAnnotationResponse, TableViewResponse]:

    rFormat = ResponseFormat.generic().validate(format, "format", ResponseFormat)
    rView = ResponseView.table().validate(view, "view", ResponseView)
    helper = GenomicsRouteHelper(
        internal,
        ResponseConfiguration(
            content=ResponseContent.FULL,
            format=rFormat,
            view=rView,
            model=VariantAnnotationResponse,
        ),
        Parameters(id=variant.feature_id),
        query=VariantFrequencyQuery,
    )

    return await helper.get_query_response()
