from fastapi import Query
from niagads.exceptions.core import ValidationError
from niagads.genome.core import Assembly, GenomicFeatureType, Human
from niagads.open_access_api_common.models.records.features.genomic import (
    GenomicFeature,
)
from niagads.utils.string import matches, sanitize


async def assembly_param(
    assembly: Assembly = Query(
        Assembly.GRCh38, description="reference genome build (assembly)"
    )
):
    return Assembly.validate(assembly, "Genome Build", Assembly)


async def chromosome_param(
    chromosome: str = Query(
        Human.chr19.value,
        enum=[c.name for c in Human],
        description="chromosome, specificed as 1..22,X,Y,M,MT or chr1...chr22,chrX,chrY,chrM,chrMT",
    )
):
    try:
        return Human.validate(sanitize(chromosome))
    except KeyError:
        raise ValidationError(f"Invalid chromosome {chromosome}.")


async def span_param(
    span: str = Query(
        description="genomic region to query; ",
        examples=["chr19:10000-40000", "19:10000-40000"],
    )
):
    return GenomicFeature.validate_span(sanitize(span))


async def loc_param(
    loc: str = Query(
        description="""genomic region to query, may be one of the following:
                Official Gene Symbol, Ensembl ID, Entrez ID, refSNP ID, variant positional ID (chr:pos:ref:alt),
                or genomic span. Please specific genomic spans as chrN:start-end or N:start-end"""
    ),
):

    location = sanitize(loc)

    try:
        return GenomicFeature(feature_id=location, feature_type=GenomicFeatureType.SPAN)
    except ValidationError:
        try:
            return GenomicFeature(
                feature_id=location, feature_type=GenomicFeatureType.VARIANT
            )
        except ValidationError:
            try:
                return GenomicFeature(
                    feature_id=location, feature_type=GenomicFeatureType.GENE
                )
            except ValidationError:
                raise ValidationError(
                    f"Invalid genomic location or feature identifier: {loc}"
                )
