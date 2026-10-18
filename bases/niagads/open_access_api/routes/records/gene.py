"""Gene record endpoints for the NIAGADS Open Access API."""

from typing import Union

from fastapi import APIRouter, Depends, Path, Query
from niagads.api.common.models.context.response import ResponseConfiguration
from niagads.api.common.models.entities.gene.records import GeneBrief, Gene
from niagads.api.common.models.responses.records import RecordMappingResponse
from niagads.api.common.parameters.response.response import (
    record_response_content_param,
    record_response_format_param,
    response_format_param,
)
from niagads.api.common.parameters.validators import parse_comma_separated_list
from niagads.api.common.services.base import BaseEndpointService
from niagads.api.common.services.gene import GeneEndpointService
from niagads.api.common.types import ResponseContent, ResponseFormat
from niagads.api.common.utils import sanitize
from niagads.common.genomic.features.models import GenomicFeature
from niagads.common.genomic.features.types import GenomicFeatureType
from niagads.open_access_api.dependencies import OpenAccessEndpointContext

router = APIRouter(prefix="/record/gene", tags=["Gene"])


# -------------------------------------------
# Record-specific parameters
# -------------------------------------------
async def path_gene_id(
    gene: str = Path(
        title="Gene identifier",
        description="Gene record identifier: Ensembl ID or official gene symbol",
        examples=["ENSG00000139618", "APOE"],
    ),
) -> str:
    return GenomicFeature(
        feature_id=sanitize(gene), feature_type=GenomicFeatureType.GENE
    ).feature_id


async def query_gene_id(
    gene: list[str] = Query(
        title="Gene identifiers",
        description="A list of one or more gene record identifier: Ensembl ID or official gene symbol",
        examples=["ENSG00000139618", "APOE"],
    ),
) -> list[str]:
    return [
        GenomicFeature(
            feature_id=sanitize(g), feature_type=GenomicFeatureType.GENE
        ).feature_id
        for g in parse_comma_separated_list(gene)
    ]


# -------------------------------------------
# Routes
# -------------------------------------------


@router.get(
    "/",
    summary="Get gene records",
    description="Retrieve the canonical record for the specified gene(s).",
    response_description="Gene records.",
    operation_id="getGenes",
    response_model=Union[RecordMappingResponse[Gene], RecordMappingResponse[GeneBrief]],
)
async def get_genes(
    gene: str = Depends(query_gene_id),
    context: OpenAccessEndpointContext = Depends(),
    format: ResponseFormat = Depends(record_response_format_param),
    content: ResponseContent = Depends(record_response_content_param),
) -> RecordMappingResponse:
    """Return a gene record.

    Args:
        gene (GenomicFeature): Validated gene identifier.
    """
    record_model = GeneBrief if context == ResponseContent.SUMMARY else Gene
    service = GeneEndpointService(
        context=context,
        parameters=None,
        response_config=ResponseConfiguration(
            format=format,
            content=content,
            response_model=RecordMappingResponse,
            record_model=record_model,
        ),
    )

    result = await service.get_record_mappings([gene])
    return await service.generate_response(result)


@router.get(
    "/{gene}",
    summary="Get gene record",
    description="Retrieve the canonical record for the specified gene.",
    response_description="Gene record.",
    operation_id="getGene",
    response_model=GeneResponse,
)
async def get_gene(
    gene: GenomicFeature = Depends(path_gene_id),
    context: OpenAccessEndpointContext = Depends(),
    format: ResponseFormat = Depends(record_response_format_param),
    content: ResponseContent = Depends(record_response_content_param),
) -> GeneResponse:
    """Return a gene record.

    Args:
        gene (GenomicFeature): Validated gene identifier.
    """

    service = BaseEndpointService(
        context=context,
        parameters=None,
        response_config=ResponseConfiguration(
            format=format, content=content, model=GeneResponse
        ),
    )

    raise NotImplementedError(f"Gene record endpoint is not implemented: {gene}")


@router.get(
    "/{gene}/associations",
    summary="Get gene associations",
    description="Retrieve genetic and phenotype associations for the specified gene.",
    response_description="Gene associations.",
    operation_id="getGeneAssociations",
)
async def get_gene_associations(
    gene: GenomicFeature = Depends(path_gene_id),
    context: OpenAccessEndpointContext = Depends(),
    format: ResponseFormat = Depends(response_format_param),
) -> None:
    """Return associations for a gene.

    Args:
        gene (GenomicFeature): Validated gene identifier.
    """

    raise NotImplementedError(f"Gene associations endpoint is not implemented: {gene}")
