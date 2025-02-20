from api.models.query_defintion import QueryDefinition
from api.routers.genomics.models.feature_score import QTL, VariantPValueScore

_BUILD_LOCATION_SQL="jsonb_build_object('chromosome', r.chromosome, 'start', r.position)  AS location"

_BUILD_VARIANT_DETAILS_SQL="""
    jsonb_build_object(
        'ref_snp_id', details->>'ref_snp_id', 
        'type', details->>'variant_class_abbrev',
        'is_adsp_variant', details->>'is_adsp_variant',
        'most_severe_consequence', jsonb_build_object(
            'consequence', details->'most_severe_consequence'->>'conseq',
            'impact', details->'most_severe_consequence'->>'impact',
            'impacted_gene', jsonb_build_object(
                'ensembl_id', details->'most_severe_consequence'->>'impacted_gene',
                'gene_symbol', details->'most_severe_consequence'->>'impacted_gene_symbol'
            ),
            'is_coding', details->'most_severe_consequence'->>'is_coding'
        ),
        'variant_id', 
            CASE WHEN split_part((details->>'metaseq_id')::text, ':', 4) = test_allele 
            THEN details->>'metaseq_id' ELSE generate_alt_metaseq_id(details->>'metaseq_id') END
    ) AS variant
"""

_TRACK_QTL_QUERY_SQL=f"""
    SELECT ta.track AS track_id, 
    r.pvalue_display AS p_value, 
    r.neg_log10p_value DESC,
    r.test_allele,
    r.dist_to_target, r.other_stats->>'z_score_non_ref' AS z_score,
    jsonb_build_object(
        'ensembl_id', target_ensembl_id, 
        'gene_symbol', ga.gene_symbol
    ) AS gene,
    
    {_BUILD_LOCATION_SQL},
    {_BUILD_VARIANT_DETAILS_SQL}

    FROM Results.QTL r,
    CBIL.GeneAttributes ga,
    NIAGADS.TrackAttributes ta,
    get_variant_display_details(r.variant_record_primary_key) as vd
    WHERE ta.protocol_app_node_id = r.protocol_app_node_id
    AND ga.source_id = r.target_ensembl_id
    ORDER BY r.neg_log10_pvalue DESC
"""

_TRACK_GSS_QUERY_SQL="""
    SELECT r.track AS track_id, 
    r.pvalue_display AS p_value, 
    r.neg_log10p_value DESC,
    r.test_allele,
    
    {_BUILD_LOCATION_SQL},
    {_BUILD_VARIANT_DETAILS_SQL}

    FROM NIAGADS.VariantGWASTopHits r,
    get_variant_display_details(r.variant_record_primary_key) as vd
    ORDER BY r.neg_log10_pvalue DESC
"""


TrackQTLQuery = QueryDefinition(
    query=_TRACK_QTL_QUERY_SQL,
    useIdSelectWrapper=True,
    errorOnNull="xQTL track not found in the NIAGADS Alzheimer's GenomicsDB"
)
    
TrackGWASSumStatQuery = QueryDefinition(
    query = _TRACK_GSS_QUERY_SQL,
    useIdSelectWrapper=True,
    errorOnNull="GWAS summary statistics track not found in the NIAGADS Alzheimer's GenomicsDB"
)