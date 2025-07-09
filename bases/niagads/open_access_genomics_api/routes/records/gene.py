from typing import Union
from fastapi import APIRouter, Depends, Query
from niagads.open_access_api_common.config.constants import SharedOpenAPITags

from niagads.open_access_api_common.models.annotations.associations import (
    GeneticAssociationResponse,
)
from niagads.open_access_api_common.models.features.gene import (
    AbridgedGeneResponse,
    GeneAnnotationResponse,
    GeneResponse,
)
from niagads.open_access_api_common.models.features.genomic import GenomicFeature
from niagads.open_access_api_common.models.services.query import QueryFilter
from niagads.open_access_api_common.parameters.associations import (
    GWASSource,
    GWASTrait,
    gwas_source_param,
    gwas_trait_param,
    neg_log10_pvalue,
    pvalue_filter_param,
)
from niagads.open_access_api_common.parameters.pagination import page_param
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
from niagads.open_access_genomics_api.queries.gene import (
    GeneAssociationsQuery,
    GeneFunctionQuery,
    GenePathwayQuery,
    GeneRecordQuery,
)
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
        ResponseContent.FULL,
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
        query=GeneRecordQuery,
    )

    return await helper.get_query_response()


tags = []


@router.get(
    "/{gene}/pathways",
    response_model=Union[GeneAnnotationResponse, TableViewResponse],
    name="Get gene pathway membership",
    description="",
)
async def get_gene_pathways(
    gene: GenomicFeature = Depends(gene_param),
    format: str = Query(
        ResponseFormat.JSON, description=ResponseFormat.generic(description=True)
    ),
    view: str = Query(
        ResponseView.DEFAULT, description=ResponseView.table(description=True)
    ),
    internal: InternalRequestParameters = Depends(),
) -> Union[GeneAnnotationResponse, TableViewResponse]:

    rFormat = ResponseFormat.generic().validate(format, "format", ResponseFormat)
    rView = ResponseView.table().validate(view, "view", ResponseView)
    helper = GenomicsRouteHelper(
        internal,
        ResponseConfiguration(
            content=ResponseContent.FULL,
            format=rFormat,
            view=rView,
            model=GeneAnnotationResponse,
        ),
        Parameters(id=gene.feature_id),
        query=GenePathwayQuery,
    )

    return await helper.get_query_response()


@router.get(
    "/{gene}/function",
    response_model=Union[GeneAnnotationResponse, TableViewResponse],
    name="Get gene-GO associations",
    description="",
)
async def get_gene_function(
    gene: GenomicFeature = Depends(gene_param),
    format: str = Query(
        ResponseFormat.JSON, description=ResponseFormat.generic(description=True)
    ),
    view: str = Query(
        ResponseView.DEFAULT, description=ResponseView.table(description=True)
    ),
    internal: InternalRequestParameters = Depends(),
) -> Union[GeneAnnotationResponse, TableViewResponse]:

    rFormat = ResponseFormat.generic().validate(format, "format", ResponseFormat)
    rView = ResponseView.table().validate(view, "view", ResponseView)
    helper = GenomicsRouteHelper(
        internal,
        ResponseConfiguration(
            content=ResponseContent.FULL,
            format=rFormat,
            view=rView,
            model=GeneAnnotationResponse,
        ),
        Parameters(id=gene.feature_id),
        query=GeneFunctionQuery,
    )

    return await helper.get_query_response()


@router.get(
    "/{gene}/associations",
    response_model=Union[GeneticAssociationResponse, TableViewResponse],
    name="Get genetic associations",
    description="Retrieve genetic associations (GWAS) for variants proximal to (+/- 1000kb) or contained within a gene footprint",
)
async def get_gene_genetic_associations(
    gene: GenomicFeature = Depends(gene_param),
    source: GWASSource = Depends(gwas_source_param),
    trait: GWASTrait = Depends(gwas_trait_param),
    page: int = Depends(page_param),
    pvalue: float = Depends(pvalue_filter_param),
    format: str = Query(
        ResponseFormat.JSON, description=ResponseFormat.generic(description=True)
    ),
    view: str = Query(
        ResponseView.DEFAULT, description=ResponseView.table(description=True)
    ),
    internal: InternalRequestParameters = Depends(),
) -> Union[GeneticAssociationResponse, TableViewResponse]:

    rContent = ResponseContent.FULL
    rFormat = ResponseFormat.generic().validate(format, "format", ResponseFormat)
    rView = ResponseView.table().validate(view, "view", ResponseView)
    helper = GenomicsRouteHelper(
        internal,
        ResponseConfiguration(
            content=rContent,
            format=rFormat,
            view=rView,
            model=GeneticAssociationResponse,
        ),
        Parameters(
            id=gene.feature_id,
            gwas_trait=trait,
            gwas_source=source,
            page=page,
            pvalue=pvalue,
            filter=(
                None
                if pvalue is None
                else QueryFilter(
                    field="neg_log10_pvalue",
                    value=neg_log10_pvalue(pvalue),
                    operator=">=",
                )
            ),
        ),
        query=GeneAssociationsQuery,
    )

    return await helper.get_query_response()
