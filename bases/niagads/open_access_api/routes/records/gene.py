"""Gene record endpoints for the NIAGADS Open Access API."""

import logging
from typing import Union

from fastapi import APIRouter, Depends, Path, Query
from niagads.api.common.models.annotations.associations import VariantAssociation
from niagads.api.common.models.context.request import Parameters
from niagads.api.common.models.context.response import ResponseConfiguration
from niagads.api.common.models.entities.gene.records import GeneBrief, Gene
from niagads.api.common.models.records.types import DynamicRecord
from niagads.api.common.models.responses.records import (
    RecordMappingResponse,
    RecordResponse,
)
from niagads.api.common.parameters.location import flank_param
from niagads.api.common.parameters.response.pagination import page_param
from niagads.api.common.parameters.response.response import (
    data_response_content_param,
    record_response_content_param,
    record_response_format_param,
    response_format_param,
)
from niagads.api.common.parameters.validators import parse_comma_separated_list
from niagads.api.common.services.gene import GeneEndpointService
from niagads.api.common.types import ResponseContent, ResponseFormat
from niagads.api.common.utils import sanitize
from niagads.common.genomic.features.models import GenomicFeature
from niagads.common.genomic.features.types import GenomicFeatureType
from niagads.open_access_api.dependencies import OpenAccessEndpointContext

logger = logging.getLogger(f"uvicorn.error.{__name__}")

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
    ids: str = Query(
        title="Gene identifiers",
        description="A list of one or more gene record identifier: Ensembl ID or official gene symbol",
        examples=["ENSG00000139618", "APOE"],
    ),
) -> list[str]:
    return [
        GenomicFeature(
            feature_id=sanitize(g), feature_type=GenomicFeatureType.GENE
        ).feature_id
        for g in parse_comma_separated_list(ids)
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
    ids: str = Depends(query_gene_id),
    context: OpenAccessEndpointContext = Depends(),
    format: ResponseFormat = Depends(record_response_format_param),
    content: ResponseContent = Depends(record_response_content_param),
    page: int = Depends(page_param),
) -> RecordMappingResponse:

    record_model = GeneBrief if content == ResponseContent.SUMMARY else Gene
    service = GeneEndpointService(
        context=context,
        parameters=Parameters(genes=ids, page=page),
        response_config=ResponseConfiguration(
            format=format,
            content=content,
            response_model=RecordMappingResponse,
            record_model=record_model,
        ),
    )

    result = await service.get_cached_response()
    from_cache = True
    if not result:
        result = await service.get_record_mappings(ids)
        from_cache = False
    response = await service.generate_response(result, from_cache=from_cache)
    return response


@router.get(
    "/{gene}",
    summary="Get gene record",
    description="Retrieve the canonical record for the specified gene.",
    response_description="Gene record.",
    operation_id="getGene",
    response_model=Union[RecordResponse[Gene], RecordResponse[GeneBrief]],
)
async def get_gene(
    gene: str = Depends(path_gene_id),
    context: OpenAccessEndpointContext = Depends(),
    format: ResponseFormat = Depends(record_response_format_param),
    content: ResponseContent = Depends(record_response_content_param),
) -> RecordResponse:

    record_model = GeneBrief if content == ResponseContent.SUMMARY else Gene
    service = GeneEndpointService(
        context=context,
        parameters=Parameters(gene=gene),
        response_config=ResponseConfiguration(
            format=format,
            content=content,
            response_model=RecordResponse,
            record_model=record_model,
        ),
    )

    result = await service.get_cached_response()
    from_cache = True
    if not result:
        result = await service.fetch_record(gene)
        from_cache = False
    response = await service.generate_response(result, from_cache=from_cache)
    return response


@router.get(
    "/{gene}/associations",
    summary="Get gene associations",
    description="Retrieve genetic and phenotype associations for the specified gene.",
    response_description="Gene associations.",
    operation_id="getGeneAssociations",
    response_model=Union[
        RecordResponse[VariantAssociation], RecordResponse[DynamicRecord]
    ],
)
async def get_gene_associations(
    gene: GenomicFeature = Depends(path_gene_id),
    flank: int = Depends(flank_param),
    context: OpenAccessEndpointContext = Depends(),
    format: ResponseFormat = Depends(response_format_param),
    content: ResponseContent = Depends(data_response_content_param),
    page: int = Depends(page_param),
) -> RecordResponse:

    summary = content == ResponseContent.SUMMARY

    record_model = DynamicRecord if summary else VariantAssociation

    service = GeneEndpointService(
        context=context,
        parameters=Parameters(gene=gene, flank=flank, page=page),
        response_config=ResponseConfiguration(
            format=format,
            content=content,
            response_model=RecordResponse,
            record_model=record_model,
        ),
    )

    result = await service.get_cached_response()
    from_cache = True
    if not result:
        result = await service.fetch_associations(gene, flank=flank, summary=summary)
        from_cache = False
    response = await service.generate_response(result, from_cache=from_cache)
    return response


@router.get(
    "/{gene}/structure",
    summary="Get gene structure",
    description="Retrieve transcripts, exons, and protein identifiers for the specified gene.",
    response_description="Gene structure.",
    operation_id="getGeneStructure",
    response_model=RecordResponse[DynamicRecord],
)
async def get_gene_structure(
    gene: GenomicFeature = Depends(path_gene_id),
    context: OpenAccessEndpointContext = Depends(),
) -> RecordResponse:

    service = GeneEndpointService(
        context=context,
        parameters=Parameters(gene=gene),
        response_config=ResponseConfiguration(
            format=ResponseFormat.JSON,
            content=ResponseContent.FULL,
            response_model=RecordResponse,
            record_model=DynamicRecord,
        ),
    )

    result = await service.get_cached_response()
    from_cache = True
    if not result:
        result = await service.fetch_gene_structure(gene)
        from_cache = False
    response = await service.generate_response(result, from_cache=from_cache)
    return response
