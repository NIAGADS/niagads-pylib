from api.models.query_defintion import QueryDefinition

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

_TRACK_QTLGENE_QUERY_SQL=f"""
    SELECT r.track_id, r.track_id AS id,
    r.pvalue_display AS p_value, 
    r.neg_log10_pvalue,
    r.test_allele,
    r.dist_to_target, r.other_stats->>'z_score_non_ref' AS z_score,
    r.chromosome,
    r.position,
    r.target_ensembl_id,
    jsonb_build_object(
        'ensembl_id', r.target_ensembl_id, 
        'gene_symbol', ga.gene_symbol
    ) AS target,

    {_BUILD_VARIANT_DETAILS_SQL}

    FROM Results.QTLGene r,
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

_TRACK_QTLGENE_COUNTS_QUERY_SQL="""
    SELECT track_id, COUNT(qtl_gene_id) AS result_size 
    FROM Results.QTLGene
    WHERE track_id = :id
    GROUP BY track_id
"""

TrackQTLGeneQuery = QueryDefinition(
    query=_TRACK_QTLGENE_QUERY_SQL,
    countsQuery=_TRACK_QTLGENE_COUNTS_QUERY_SQL,
    useIdSelectWrapper=True,
    errorOnNull="xQTL track not found in the NIAGADS Alzheimer's GenomicsDB",
    messageOnResultSize="Found target {0} genes in this analysis.  Displaying {1}.  To retrieve the full set, please run the following `paged` query using the NIAGADS Open Access API: {2}.",
    bindParameters = ['rank_start', 'rank_end']
)
    
TrackGWASSumStatQuery = QueryDefinition(
    query = _TRACK_GSS_QUERY_SQL,
    useIdSelectWrapper=True,
    errorOnNull="GWAS summary statistics track not found in the NIAGADS Alzheimer's GenomicsDB"
)

# TODO: make generic like the data queries
CountsTrackSummaryQuery = QueryDefinition(
    query="""
        SELECT chromosome, count(target_ensembl_id)
        FROM Results.QTLGene
        WHERE track_id = :id
        GROUP BY track_id, chromosome
        ORDER BY replace(chromosome, 'chr', '')::integer
    """,
    bindParameters = ['id'],
    errorOnNull="xQTL track not found in the NIAGADS Alzheimer's GenomicsDB",
    rawResponse = True
)

TopTrackSummaryQuery = QueryDefinition(
    query="""
        SELECT r.chromosome, 
        vd.details->>'ref_snp_id' AS ref_snp_id, vd.details->>'metaseq_id' AS variant,
        vd.details->>'is_adsp_variant' AS is_adsp_variant,
        ga.gene_symbol,
        to_char(r.neg_log10_pvalue, 'FM999999999.00') AS neg_log10_pvalue
        FROM Results.QTLGene r, CBIL.GeneAttributes ga,  get_variant_display_details(r.variant_record_primary_key) as vd
        WHERE ga.source_id = r.target_ensembl_id
        AND r.rank <= 10
        AND r.track_id = :id
        ORDER BY r.rank ASC
    """,
    bindParameters = ['id'],
    errorOnNull="xQTL track not found in the NIAGADS Alzheimer's GenomicsDB",
    rawResponse = True
)