from typing import Annotated

from fastapi import Query
from pydantic import BeforeValidator
from components.niagads.api.common.parameters.validators import (
    sanitize_enum_value,
    sanitize_value,
)

from niagads.common.genomic.features.models import GenomicFeature
from niagads.common.genomic.features.types import GenomicFeatureType
from niagads.exceptions.core import ValidationError
from niagads.genome_reference.human import GenomeBuild, HumanGenome


async def assembly_param(
    assembly: Annotated[
        GenomeBuild,
        BeforeValidator(sanitize_enum_value(GenomeBuild)),
        Query(
            description=(
                "Reference genome assembly used to interpret genomic coordinates. "
                "Supported assemblies are GRCh37 and GRCh38; hg19 and hg38 are "
                "accepted as aliases."
            )
        ),
    ] = GenomeBuild.GRCh38,
):
    return assembly


async def chromosome_param(
    chromosome: Annotated[
        HumanGenome,
        BeforeValidator(sanitize_enum_value(HumanGenome)),
        Query(
            alias="chr",
            description=(
                "Chromosome identifier. Use 1–22, X, Y, M, or MT, or the equivalent "
                "chr-prefixed form (for example, chr19 or chrM)."
            ),
        ),
    ] = HumanGenome.chr19,
):
    return chromosome


async def location_param(
    location: str = Query(
        alias="loc",
        description=(
            "Location to query. Accepted values are Official Gene Symbols, "
            "Ensembl or Entrez (NBCU) Gene identifiers, refSNP identifiers, positional variant identifiers "
            "(chr:position:reference:alternate), or a genomic span specified as chrN:start-end or N:start-end."
        ),
    )
):

    location = sanitize_value(location)

    for feature_type in (
        GenomicFeatureType.REGION,
        GenomicFeatureType.VARIANT,
        GenomicFeatureType.GENE,
    ):
        try:
            return GenomicFeature(
                feature_id=location,
                feature_type=feature_type,
            )
        except ValueError:
            continue

    raise ValueError(f"Invalid genomic location or feature identifier: {location}")
