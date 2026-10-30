from typing import Optional

from fastapi import Path, Query
from niagads.api.common.parameters.validators import parse_comma_separated_list
from niagads.api.common.utils import sanitize
from niagads.common.genomic.features.models import GenomicFeature
from niagads.common.genomic.features.types import GenomicFeatureType
from niagads.common.genomic.regions.models import OneBasedGenomicRegion
from niagads.exceptions.core import ValidationError


async def collection_id(
    collection_id: str = Path(
        description="Unique, stable identifier (e.g., NIAGADS acccesion number) identifying a track collection."
    ),
) -> str:
    return sanitize(collection_id)


async def track_id_query_param(
    track: Optional[str] = Query(
        default=None,
        description="Track (data file) identifier (FILER Accession or DSS File ID)",
    )
) -> str:
    track_id: str = sanitize(track)
    if track_id is not None and "," in track_id:
        raise ValidationError(
            "Lists of track identifiers not allowed for this query.  Please provide a single `track` identifier."
        )
    return track_id


async def multi_track_id_query_param(
    track_ids: str = Query(
        description="Comma separated list of one or more Track (data file) identifier (FILER Accession or DSS File ID)",
    )
) -> list[str]:
    """required track_list parameter"""
    return parse_comma_separated_list(sanitize(track_ids))


async def region_id(
    region: str = Path(
        description=(
            "Genomic region: chrN:start-end or N:start-end, where N is the "
            "chromosome number. The span must be less than 100,000 bp."
        )
    ),
):
    feature = GenomicFeature(
        feature_id=sanitize(region), feature_type=GenomicFeatureType.REGION
    )
    location = OneBasedGenomicRegion.from_region_id(feature.feature_id)
    if location.end - location.start + 1 >= 100_000:
        raise ValidationError("Region span must be less than 100,000 bp.")
    return feature


async def variant_id(
    variant: str = Path(
        description="variant record identifier; refSNP ID or positional allele (chr:pos:ref:alt)"
    ),
):
    return GenomicFeature(
        feature_id=sanitize(variant), feature_type=GenomicFeatureType.VARIANT
    )
