from typing import Optional
from fastapi import Path, Query
from niagads.api.common.models.domain.parameters.utils import parse_comma_separated_list
from niagads.api.common.utils import sanitize
from niagads.common.genomic.features.models import GenomicFeature
from niagads.common.genomic.features.types import GenomicFeatureType
from niagads.exceptions.core import ValidationError


async def collection_id(
    collection: str = Path(
        description="Unique, stable identifier (e.g., NIAGADS acccesion number) identifying a track collection."
    ),
) -> str:
    return sanitize(collection)


async def track_id(
    track_id: str = Path(
        description="Track (data file) identifier (FILER Accession or DSS File ID)"
    ),
) -> str:
    return sanitize(track_id)


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
    track: str = Query(
        description="Comma separated list of one or more Track (data file) identifier (FILER Accession or DSS File ID)",
    )
) -> list[str]:
    """required track_list parameter"""
    return parse_comma_separated_list(sanitize(track))


async def gene_id(
    gene: str = Path(
        description="gene record identifier; Ensembl ID, Official Gene Symbol or Entrez (NCBI) gene ID"
    ),
):
    return GenomicFeature(
        feature_id=sanitize(gene), feature_type=GenomicFeatureType.GENE
    )


async def region_id(
    region: str = Path(
        description="genomic region: chrN:start-end or N:start-end, where N is the chromosome number"
    ),
):
    return GenomicFeature(
        feature_id=sanitize(region), feature_type=GenomicFeatureType.REGION
    )


async def variant_id(
    variant: str = Path(
        description="variant record identifier; refSNP ID or positional allele (chr:pos:ref:alt)"
    ),
):
    return GenomicFeature(
        feature_id=sanitize(variant), feature_type=GenomicFeatureType.VARIANT
    )
