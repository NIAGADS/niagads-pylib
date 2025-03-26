from api.models.query_defintion import QueryDefinition
from api.routers.genomics.models.feature_score import QTL, VariantPValueScore



_BUILD_VARIANT_DETAILS_SQL="""
    jsonb_build_object(
        'ref_snp_id', details->>'ref_snp_id', 
        'type', details->>'variant_class_abbrev',
        'is_adsp_variant', CASE WHEN details->>'is_adsp_variant' IS NULL 
                                THEN FALSE ELSE (details->>'is_adsp_variant')::bool END,
        'most_severe_consequence', jsonb_build_object(
            'consequence', details->'most_severe_consequence'->>'conseq',
            'impact', details->'most_severe_consequence'->>'impact',
            
            'impacted_gene', CASE WHEN details->'most_severe_consequence'->>'impacted_gene' IS NOT NULL 
                THEN 
                    CASE WHEN (SELECT gene_symbol FROM CBIL.GeneAttributes WHERE source_id = details->'most_severe_consequence'->>'impacted_gene' LIMIT 1) IS NOT NULL THEN
                    jsonb_build_object(
                    'ensembl_id', details->'most_severe_consequence'->>'impacted_gene',
                    'gene_symbol', (SELECT gene_symbol FROM CBIL.GeneAttributes WHERE source_id = details->'most_severe_consequence'->>'impacted_gene' LIMIT 1)
                        ) ELSE NULL END
                ELSE NULL END,

            'is_coding', details->'most_severe_consequence'->>'is_coding'
        ),
        'variant_id', 
            CASE WHEN split_part((details->>'metaseq_id')::text, ':', 4) = test_allele 
            THEN details->>'metaseq_id' ELSE generate_alt_metaseq_id(details->>'metaseq_id') END
    ) AS variant
"""

_TRACK_QTL_QUERY_SQL=f"""
    SELECT r.track_id,
    r.pvalue_display AS p_value, 
    r.neg_log10_pvalue,
    r.test_allele,
    r.dist_to_target, r.other_stats->>'z_score_non_ref' AS z_score,
    r.chromosome,
    r.position,
    jsonb_build_object(
        'ensembl_id', target_ensembl_id, 
        'gene_symbol', ga.gene_symbol
    ) AS target,

    {_BUILD_VARIANT_DETAILS_SQL}

    FROM Results.QTL r,
    CBIL.GeneAttributes ga,
    get_variant_display_details(r.variant_record_primary_key) as vd
    WHERE ga.source_id = r.target_ensembl_id
    AND (rank > :rank_start AND rank <= :rank_end) -- ranks are 1-based, pagination is 0-based
    ORDER BY rank ASC
"""

_TRACK_GSS_QUERY_SQL=f"""
    SELECT r.track AS track_id, r.track AS id,
    r.pvalue_display AS p_value, 
    r.neg_log10_pvalue,
    r.test_allele,
    r.position,
    r.chromosome,
    
    {_BUILD_VARIANT_DETAILS_SQL}

    FROM NIAGADS.VariantGWASTopHits r,
    get_variant_display_details(r.variant_record_primary_key) as vd
    ORDER BY r.neg_log10_pvalue DESC
"""

_TRACK_QTL_COUNTS_QUERY_SQL="""
    SELECT source_id AS track_id,
    CASE WHEN (track_summary->>'number_of_intervals')::int > 10000 
    THEN 10000 ELSE (track_summary->>'number_of_intervals')::int END
    AS result_size 
    FROM Study.ProtocolAppNode
    WHERE source_id = :id
"""

TrackQTLQuery = QueryDefinition(
    query=_TRACK_QTL_QUERY_SQL,
    countsQuery=_TRACK_QTL_COUNTS_QUERY_SQL,
    useIdSelectWrapper=True,
    errorOnNull="xQTL track not found in the NIAGADS Alzheimer's GenomicsDB",
    bindParameters = ['rank_start', 'rank_end']
)
    
TrackGWASSumStatQuery = QueryDefinition(
    query = _TRACK_GSS_QUERY_SQL,
    useIdSelectWrapper=True,
    errorOnNull="GWAS summary statistics track not found in the NIAGADS Alzheimer's GenomicsDB"
)

