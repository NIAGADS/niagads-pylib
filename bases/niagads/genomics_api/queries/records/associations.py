GWAS_TRACK_CTE = """
    SELECT track_id, name AS track_name,
        provenance->>'data_source' AS data_source,
        provenance->'pubmed_id' AS pubmed_id,
        subject_phenotypes,
        biosample_characteristics,
        CASE WHEN (subject_phenotypes->'disease')::text LIKE '%Alzh%' THEN 'AD'
        WHEN biosample_characteristics IS NOT NULL THEN 'Biomarker'
        WHEN (subject_phenotypes->'disease')::text 
        NOT LIKE '%Alzh%' OR subject_phenotypes->'neuropathology' IS NOT NULL THEN 'ADRD'
        ELSE NULL END AS category
    FROM Dataset.Track
    WHERE 
        feature_type = 'variant'
        AND experimental_design->>'classification' = 'genetic association' 
        AND ((:association_source IN ('GWAS', 'ALL') 
            AND experimental_design->>'data_category' = 'summary statistics')
        OR (:association_source IN ('CURATED', 'ALL') 
            AND experimental_design->>'data_category' = 'curated'))
"""


GWAS_COMMON_FIELDS = """
    t.track_id, 
    CASE WHEN r.restricted_stats->'trait' is NOT NULL 
        THEN r.restricted_stats->>'study'
        ELSE t.track_name 
    END AS track_name,
    t.data_source,
    t.subject_phenotypes,
    t.biosample_characteristics,
    CASE WHEN t.category IS NOT NULL 
        THEN t.category 
        ELSE COALESCE((SELECT category 
            FROM NIAGADS.ADTerms 
            WHERE term_id = replace(r.restricted_stats->>'efo_uri','http://www.ebi.ac.uk/efo/', '')),
            'Other') 
        END AS trait_category,
    CASE WHEN r.restricted_stats->'trait' IS NOT NULL 
        THEN to_jsonb(ARRAY['PMID:' || replace(r.restricted_stats->>'pubmed_url', 'www.ncbi.nlm.nih.gov/pubmed/', '')]) 
        ELSE t.pubmed_id 
    END AS pubmed_id,
    jsonb_build_object(
        'variant_id', r.metaseq_id, 
        'ref_snp_id', r.ref_snp_id, 
        'variant_class', r.display_attributes->>'variant_class_abbrev', 
        'is_adsp_variant', r.is_adsp_variant,
        'most_severe_consequence',r.annotation->'adsp_most_severe_consequence'
    ) AS variant,
    r.test_allele,
    TRIM(TO_CHAR(r.pvalue_display::numeric, '9.99EEEE')) AS p_value,
    neg_log10_pvalue,
    CASE WHEN r.restricted_stats->'trait' is NOT NULL 
        THEN jsonb_build_object(
            'term', r.restricted_stats->>'trait', 
            'term_id', replace(r.restricted_stats->>'efo_uri', 'http://www.ebi.ac.uk/efo/', '')) 
        ELSE NULL 
    END AS trait
"""

association_trait_FILTERS = """
    WHERE ((UPPER(:association_trait) IN ('AD', 'ALL_AD', 'ALL') AND trait_category = 'AD')
    OR (UPPER(:association_trait) IN ('BIOMARKER', 'ALL_AD', 'ALL') AND trait_category = 'Biomarker')
    OR (UPPER(:association_trait) IN ('ADRD', 'ALL_AD', 'ALL') AND trait_category = 'ADRD')
    OR (UPPER(:association_trait) IN ('OTHER', 'ALL') AND trait_category = 'Other'))            
"""
