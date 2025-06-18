"""record ID path parameters"""

from typing import Optional
from fastapi import Path, Query
from niagads.exceptions.core import ValidationError
from niagads.genome.core import GenomicFeatureType
from niagads.open_access_api_common.models.records.features.genomic import (
    GenomicFeature,
)
from niagads.utils.string import sanitize


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


async def gene_param(gene: str = Path(description="")):
    return GenomicFeature(
        feature_id=sanitize(gene), feature_type=GenomicFeatureType.GENE
    )
