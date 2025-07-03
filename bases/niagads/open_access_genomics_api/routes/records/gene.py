from typing import Union
from fastapi import APIRouter, Depends, Path, Query
from niagads.enums.core import EnumParameter
from niagads.open_access_api_common.config.constants import SharedOpenAPITags

from niagads.open_access_api_common.models.features.gene import (
    AbridgedGeneResponse,
    GeneResponse,
)
from niagads.open_access_api_common.models.features.genomic import GenomicFeature
from niagads.open_access_api_common.models.response.core import RecordResponse
from niagads.open_access_api_common.parameters.record.path import gene_param
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
from niagads.open_access_genomics_api.queries.gene import GeneRecordQuery
from niagads.open_access_genomics_api.services.route import GenomicsRouteHelper


class GeneAttribute(EnumParameter):
    GO = "go_annotation"
    HGNC = "hgnc_annotation"
    PATHWAYS = "pathway_annotation"


async def gene_attribute_param(
    attribute: GeneAttribute = Path(description="annotation to retrieve"),
):
    return GeneAttribute.validate(attribute, "Attribute", GeneAttribute)


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


@router.get(
    "/{gene}/{attribute}",
    response_model=Union[RecordResponse, TableViewResponse],
    name="Get specific attributes only",
    description="retrieve an annotated gene",
)
async def get_gene_attribute(
    gene: GenomicFeature = Depends(gene_param),
    attribute: str = Depends(gene_attribute_param),
    format: str = Query(
        ResponseFormat.JSON, description=ResponseFormat.generic(description=True)
    ),
    view: str = Query(
        ResponseView.DEFAULT, description=ResponseView.table(description=True)
    ),
    internal: InternalRequestParameters = Depends(),
) -> Union[RecordResponse, TableViewResponse]:

    rContent = ResponseContent.FULL
    rFormat = ResponseFormat.generic().validate(format, "format", ResponseFormat)
    rView = ResponseView.table().validate(view, "view", ResponseView)
    helper = GenomicsRouteHelper(
        internal,
        ResponseConfiguration(
            content=rContent, format=rFormat, view=rView, model=RecordResponse
        ),
        Parameters(id=gene.feature_id, attribute=attribute),
        # idParameter="id",
        query=GeneRecordQuery,
    )

    return await helper.get_query_response()
