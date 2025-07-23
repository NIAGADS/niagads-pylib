from typing import Union

from fastapi import APIRouter, Depends, Query
from niagads.api_common.constants import SharedOpenAPITags
from niagads.api_common.models.annotations.associations import (
    AssociationSource,
    AssociationTrait,
    GeneticAssociationResponse,
)
from niagads.api_common.models.features.genomic import GenomicFeature
from niagads.api_common.models.features.variant import (
    AbridgedVariantResponse,
    VariantAnnotationResponse,
    VariantResponse,
)
from niagads.api_common.models.records import Entity
from niagads.api_common.models.response.core import RecordResponse
from niagads.api_common.models.services.query import QueryFilter
from niagads.api_common.parameters.associations import (
    association_source_param,
    association_trait_param,
    neg_log10_pvalue,
    pvalue_filter_param,
)
from niagads.api_common.parameters.pagination import page_param
from niagads.api_common.parameters.record.path import variant_param
from niagads.api_common.parameters.response import (
    ResponseContent,
    ResponseFormat,
    ResponseView,
)
from niagads.api_common.services.route import (
    Parameters,
    ResponseConfiguration,
)
from niagads.api_common.views.table import TableViewResponse
from niagads.genomics_api.dependencies import InternalRequestParameters
from niagads.genomics_api.documentation import APP_NAME
from niagads.genomics_api.queries.variant import (
    ColocatedVariantQuery,
    VariantAssociationsQuery,
    VariantFrequencyQuery,
    VariantRecordQuery,
)
from niagads.genomics_api.services.route import GenomicsRouteHelper, QueryOptions

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

    response_content = ResponseContent.descriptive().validate(
        content, "content", ResponseContent
    )
    response_format = ResponseFormat.generic().validate(
        format, "format", ResponseFormat
    )
    helper = GenomicsRouteHelper(
        internal,
        ResponseConfiguration(
            content=response_content,
            format=response_format,
            model=(
                VariantResponse
                if response_content == ResponseContent.FULL
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

    response_format = ResponseFormat.generic().validate(
        format, "format", ResponseFormat
    )
    response_view = ResponseView.table().validate(view, "view", ResponseView)
    helper = GenomicsRouteHelper(
        internal,
        ResponseConfiguration(
            content=ResponseContent.FULL,
            format=response_format,
            view=response_view,
            model=VariantAnnotationResponse,
        ),
        Parameters(id=variant.feature_id),
        query=VariantFrequencyQuery,
    )

    return await helper.get_query_response()


@router.get(
    "/{variant}/associations",
    response_model=Union[GeneticAssociationResponse, RecordResponse, TableViewResponse],
    name="Get genetic associations",
    description="Retrieve genetic associations (GWAS) for the variant",
)
async def get_variant_genetic_associations(
    variant: GenomicFeature = Depends(variant_param),
    source: AssociationSource = Depends(association_source_param),
    trait: AssociationTrait = Depends(association_trait_param),
    page: int = Depends(page_param),
    pvalue: float = Depends(pvalue_filter_param),
    format: str = Query(
        ResponseFormat.JSON, description=ResponseFormat.generic(description=True)
    ),
    view: str = Query(
        ResponseView.DEFAULT, description=ResponseView.table(description=True)
    ),
    content: str = Query(
        ResponseContent.FULL, description=ResponseContent.full_data(description=True)
    ),
    internal: InternalRequestParameters = Depends(),
) -> Union[GeneticAssociationResponse, RecordResponse, TableViewResponse]:

    response_format = ResponseFormat.generic().validate(
        format, "format", ResponseFormat
    )
    response_view = ResponseView.table().validate(view, "view", ResponseView)

    response_content = ResponseContent.full_data().validate(
        content, "content", ResponseContent
    )
    counts_only = response_content == ResponseContent.COUNTS

    helper = GenomicsRouteHelper(
        internal,
        ResponseConfiguration(
            content=response_content,
            format=response_format,
            view=response_view,
            model=RecordResponse if counts_only else GeneticAssociationResponse,
        ),
        Parameters(
            id=variant.feature_id,
            association_trait=trait,
            association_source=source,
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
        query=VariantAssociationsQuery,
    )

    return await helper.get_feature_annotation(
        entity=Entity.VARIANT, opts=QueryOptions(counts_only=counts_only)
    )


@router.get(
    "/{variant}/coloc_vars",
    response_model=VariantAnnotationResponse,
    name="Get co-located (or alt) variants",
    description="Retrieve variant identifiers for alternative alleles or co-located (overlapping) INDELs and SVs",
)
async def get_colocated_variants(
    variant: GenomicFeature = Depends(variant_param),
    internal: InternalRequestParameters = Depends(),
) -> VariantAnnotationResponse:

    helper = GenomicsRouteHelper(
        internal,
        ResponseConfiguration(
            content=ResponseContent.FULL,
            format=ResponseFormat.JSON,
            view=ResponseView.DEFAULT,
            model=VariantAnnotationResponse,
        ),
        Parameters(
            id=variant.feature_id,
        ),
        query=ColocatedVariantQuery,
    )

    return await helper.get_feature_annotation(entity=Entity.VARIANT)


@router.get(
    "/{variant}/function",
    response_model=VariantAnnotationResponse,
    name="Get co-located (or alt) variants",
    description="Retrieve variant identifiers for alternative alleles or co-located (overlapping) INDELs and SVs",
)
async def get_colocated_variants(
    variant: GenomicFeature = Depends(variant_param),
    internal: InternalRequestParameters = Depends(),
) -> VariantAnnotationResponse:

    helper = GenomicsRouteHelper(
        internal,
        ResponseConfiguration(
            content=ResponseContent.FULL,
            format=ResponseFormat.JSON,
            view=ResponseView.DEFAULT,
            model=VariantAnnotationResponse,
        ),
        Parameters(
            id=variant.feature_id,
        ),
        query=ColocatedVariantQuery,
    )

    return await helper.get_feature_annotation(entity=Entity.VARIANT)
