"""record ID path parameters"""

from fastapi import Path

from niagads.genomics.sequence.types import GenomicFeatureType
from niagads.api.common.parameters.igvbrowser import AnnotatedVariantTrack
from niagads.api.common.models.features.genomic import GenomicFeature
from niagads.api.common.utils import sanitize


# tracks and collections
async def track_param(track: str = Path(description="data track identifier")) -> str:
    return sanitize(track)


async def collection_param(
    collection: str = Path(description="track collection name"),
) -> str:
    return sanitize(collection)


# genomic features
async def variant_param(
    variant: str = Path(
        description="variant record identifier; refSNP ID or positional allele (chr:pos:ref:alt)"
    ),
):
    return GenomicFeature(
        feature_id=sanitize(variant), feature_type=GenomicFeatureType.VARIANT
    )


async def gene_param(
    gene: str = Path(
        description="gene record identifier; Ensembl ID, Official Gene Symbol or Entrez (NCBI) gene ID"
    ),
):
    return GenomicFeature(
        feature_id=sanitize(gene), feature_type=GenomicFeatureType.GENE
    )


async def region_param(
    region: str = Path(
        description="genomic region: chrN:start-end or N:start-end, where N is the chromosome number"
    ),
):
    # validate feature
    return GenomicFeature(feature_id=region, feature_type=GenomicFeatureType.REGION)
