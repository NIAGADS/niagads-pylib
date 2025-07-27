from niagads.api_common.models.services.query import QueryDefinition
from niagads.api_common.parameters.igvbrowser import AnnotatedVariantTrack


def select_track_query(track: AnnotatedVariantTrack):
    if "SV" in str(track):
        return SVBrowserTrackQuery
    if "ADSP" in str(track):
        return ADSPBrowserTrackQuery
    if "COMMON" in str(track):
        return DBSnpCommonBrowserTrackQuery
    return DBSnpBrowserTrackQuery


SVBrowserTrackQuery = QueryDefinition(
    query="""
        SELECT jsonb_agg(variants) AS result FROM (
        select jsonb_build_object(
        'chrom', location->>'chromosome', 
        'pos', (location->>'start')::int,
        'id', variant->>'variant_id',
        'ref', '.',
        'alt', '.',
        'qual', '.',
        'filter', '.',
        'info', jsonb_build_object(
        'location_start', location->>'start',
        'location_end', (location->>'start')::int + (location->>'length')::int,
        'display_id', variant->>'variant_id',
        'variant_id', variant->>'variant_id',
        'ref_snp_id', '.',
        'variant_class', variant->>'variant_class',
        'variant_class_abbrev', variant->>'variant_class_abbrev',
        'display_allele', variant->>'allele_string',
        'most_severe_consequence', variant->'most_severe_consequence')) as variants
        FROM sv_by_range_lookup(:chromosome, :start, :end) )
        r
    """,
    bind_parameters=["chromosome", "start", "end"],
    allow_filters=False,
    json_field="result",
)


# Define QueryDefinitions for GRCh38 track types
ADSPBrowserTrackQuery = QueryDefinition(
    query="SELECT get_adsp_variants(:chromosome, :start, :end, :adsp_release, :svs_only) AS result",
    bind_parameters=["chromosome", "start", "end", "adsp_release", "svs_only"],
    allow_filters=False,
    json_field="result",
)

DBSnpBrowserTrackQuery = QueryDefinition(
    query="SELECT get_dbsnp_variants(:chromosome, :start, :end) AS result",
    bind_parameters=["chromosome", "start", "end"],
    allow_filters=False,
    json_field="result",
)

DBSnpCommonBrowserTrackQuery = QueryDefinition(
    query="SELECT get_dbsnp_common_variants(:chromosome, :start, :end) AS result",
    bind_parameters=["chromosome", "start", "end"],
    allow_filters=False,
)
