from fastapi import Query
from fastapi.exceptions import RequestValidationError
from niagads.genome.core import Assembly, GenomicFeatureType, Human
from niagads.open_access_api_common.models.data.genome import Feature
from niagads.utils.string import matches, sanitize


async def assembly_param(
    assembly: Assembly = Query(
        Assembly.GRCh38, description="reference genome build (assembly)"
    )
):
    return Assembly.validate(assembly)


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
        raise RequestValidationError(f"Invalid chromosome {chromosome}.")


def validate_span(span: str, returnNotMatching: bool = False):
    pattern = r".+:\d+-\d+$"  # chr:start-enddddd - NOTE: the r prefix declares the pattern as a raw string so that no syntax warning gets thrown for escaping the d

    # check against regexp
    if matches(pattern, span) == False:
        if returnNotMatching:
            return False
        else:
            raise RequestValidationError(
                f"Invalid genomic span: `{span}`;"
                f"for a chromosome, N, please specify as chrN:start-end or N:start-end"
            )

    # split on :
    [chrm, coords] = span.split(":")
    try:
        validChrm = Human.validate(chrm)
    except KeyError:
        raise RequestValidationError(
            f"Invalid genomic span: `{span}`; invalid chromosome `{chrm}`"
        )

    # validate start < end
    [start, end] = coords.split("-")
    if int(start) > int(end):
        raise RequestValidationError(
            f"Invalid genomic span: `{span}`; start coordinate must be <= end"
        )
    return validChrm + ":" + coords


async def span_param(
    span: str = Query(
        description="genomic region to query; ",
        examples=["chr19:10000-40000", "19:10000-40000"],
    )
):
    return validate_span(sanitize(span))


def validate_variant(feature: str, returnNotMatching):
    pattern = r".+:\d+:[ACGT]+:[ACGT]+"

    if matches(pattern, feature) == False:
        feature = feature.lower()
        pattern = r"rs\d+"
        if matches(pattern, feature):
            return feature

        if returnNotMatching:
            return False
        else:
            raise RequestValidationError(
                f"Invalid variant: `{feature}`; please specify using the refSNP id or a positional identifier (chr:pos:ref:alt)"
            )

    # validate chrm
    [chrm, pos, ref, alt] = feature.split(":")
    try:
        Human.validate(chrm)
    except KeyError:
        raise RequestValidationError(
            f"Invalid genomic location: `{feature}`; invalid chromosome `{chrm}`"
        )

    return feature


async def loc_param(
    loc: str = Query(
        description="""genomic region to query, may be one of the following:
                Official Gene Symbol, Ensembl ID, Entrez ID, refSNP ID, variant positional ID (chr:pos:ref:alt),
                or genomic span. Please specific genomic spans as chrN:start-end or N:start-end"""
    ),
):

    location = sanitize(loc)

    value = validate_span(location, returnNotMatching=True)
    if not isinstance(value, bool):
        return Feature(feature_id=value, feature_type=GenomicFeatureType.SPAN)

    value = validate_variant(location, returnNotMatching=True)
    if not isinstance(value, bool):
        return Feature(feature_id=value, feature_type=GenomicFeatureType.VARIANT)

    return Feature(feature_id=location, feature_type=GenomicFeatureType.GENE)
