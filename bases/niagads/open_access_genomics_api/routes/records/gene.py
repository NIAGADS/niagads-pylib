from typing import Union
from fastapi import APIRouter, Depends, Query
from niagads.open_access_api_common.config.constants import SharedOpenAPITags

from niagads.open_access_api_common.models.records.features.gene import (
    AbridgedGeneResponse,
    GeneResponse,
)

from niagads.open_access_api_common.models.records.features.genomic import (
    GenomicFeature,
)
from niagads.open_access_api_common.parameters.record.path import gene_param
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
from niagads.open_access_genomics_api.queries.gene import GeneRecordQuery
from niagads.open_access_genomics_api.services.route import GenomicsRouteHelper

router = APIRouter(
    prefix="/record/gene",
    tags=[
        APP_NAME,
        str(SharedOpenAPITags.GENE_RECORD),
    ],
)


@router.get(
    "/{gene}",
    response_model=Union[AbridgedGeneResponse, GeneResponse],
    name="Get gene record",
    description="retrieve an annotated gene",
)
async def get_gene(
    gene: GenomicFeature = Depends(gene_param),
    content: str = Query(
        ResponseContent.BRIEF,
        description=ResponseContent.descriptive(description=True),
    ),
    format: str = Query(
        ResponseFormat.JSON, description=ResponseFormat.generic(description=True)
    ),
    internal: InternalRequestParameters = Depends(),
) -> Union[AbridgedGeneResponse, GeneResponse]:

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
                GeneResponse
                if rContent == ResponseContent.FULL
                else AbridgedGeneResponse
            ),
        ),
        Parameters(id=gene.feature_id),
        # idParameter="id",
        query=GeneRecordQuery,
    )

    return await helper.get_query_response()
