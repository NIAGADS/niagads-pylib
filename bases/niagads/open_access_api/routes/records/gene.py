"""Gene record endpoints for the NIAGADS Open Access API."""

from fastapi import APIRouter, Depends, Path
from niagads.api.common.parameters.response.response import (
    record_response_format_param,
    response_format_param,
)
from niagads.api.common.types import ResponseFormat
from niagads.api.common.utils import sanitize
from niagads.common.genomic.features.models import GenomicFeature
from niagads.common.genomic.features.types import GenomicFeatureType
from niagads.open_access_api.dependencies import OpenAccessContext

router = APIRouter(prefix="/record/gene", tags=["Gene"])


# -------------------------------------------
# Record path parameter
# -------------------------------------------
async def gene_id(
    gene: str = Path(
        title="Gene identifier",
        description=(
            "Gene record identifier: Ensembl ID, official gene symbol, "
            "or Entrez (NCBI) gene ID."
        ),
        examples=["ENSG00000139618", "BRCA1", "67200"],
    ),
):
    return GenomicFeature(
        feature_id=sanitize(gene), feature_type=GenomicFeatureType.GENE
    )


# -------------------------------------------
# Routes
# -------------------------------------------


@router.get(
    "/{gene}",
    summary="Get gene record",
    description="Retrieve the canonical record for the specified gene.",
    response_description="Gene record.",
    operation_id="getGene",
)
async def get_gene(
    gene: GenomicFeature = Depends(gene_id),
    internal: OpenAccessContext = Depends(),
    format: ResponseFormat = Depends(record_response_format_param),
) -> None:
    """Return a gene record.

    Args:
        gene (GenomicFeature): Validated gene identifier.
    """

    raise NotImplementedError(f"Gene record endpoint is not implemented: {gene}")


@router.get(
    "/{gene}/pathways",
    summary="Get gene pathways",
    description="Retrieve pathways associated with the specified gene.",
    response_description="Gene pathway associations.",
    operation_id="getGenePathways",
)
async def get_gene_pathways(
    gene: GenomicFeature = Depends(gene_id),
    internal: OpenAccessContext = Depends(),
    format: ResponseFormat = Depends(response_format_param),
) -> None:
    """Return pathways associated with a gene.

    Args:
        gene (GenomicFeature): Validated gene identifier.
    """

    raise NotImplementedError(f"Gene pathways endpoint is not implemented: {gene}")


@router.get(
    "/{gene}/function",
    summary="Get gene function",
    description="Retrieve functional annotations for the specified gene.",
    response_description="Gene functional annotations.",
    operation_id="getGeneFunction",
)
async def get_gene_function(
    gene: GenomicFeature = Depends(gene_id),
    internal: OpenAccessContext = Depends(),
    format: ResponseFormat = Depends(response_format_param),
) -> None:
    """Return functional annotations for a gene.

    Args:
        gene (GenomicFeature): Validated gene identifier.
    """

    raise NotImplementedError(f"Gene function endpoint is not implemented: {gene}")


@router.get(
    "/{gene}/associations",
    summary="Get gene associations",
    description="Retrieve genetic and phenotype associations for the specified gene.",
    response_description="Gene associations.",
    operation_id="getGeneAssociations",
)
async def get_gene_associations(
    gene: GenomicFeature = Depends(gene_id),
    internal: OpenAccessContext = Depends(),
    format: ResponseFormat = Depends(response_format_param),
) -> None:
    """Return associations for a gene.

    Args:
        gene (GenomicFeature): Validated gene identifier.
    """

    raise NotImplementedError(f"Gene associations endpoint is not implemented: {gene}")
