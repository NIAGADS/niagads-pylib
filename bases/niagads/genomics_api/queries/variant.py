from typing import List
from niagads.api_common.models.annotations.associations import (
    VariantAssociation,
    VariantAssociationSummary,
)
from niagads.api_common.models.records import Entity
from niagads.api_common.models.services.query import QueryDefinition
from niagads.genomics_api.queries.associations import (
    GWAS_COMMON_FIELDS,
    GWAS_TRACK_CTE,
    association_trait_FILTERS,
)


GWAS_RESULTS_CTE = f"""
    SELECT 
    {GWAS_COMMON_FIELDS}
    FROM NIAGADS.VariantGWASTopHits r, Tracks t
    WHERE t.track_id = r.track 
    AND r.metaseq_id = (SELECT find_variant_primary_key(:id))
    ORDER BY neg_log10_pvalue DESC
"""


VariantFrequencyQuery = QueryDefinition(
    query="""
        WITH variant AS (
        SELECT annotation->>'variant_id' AS variant_id,
        annotation->>'alt' AS alt,
        annotation->>'ref' AS ref,
        annotation->'allele_frequencies' AS frequencies
        FROM get_variant_primary_keys_and_annotations_tbl(:id)),

        freq_elements AS (
        SELECT variant_id, 
        alt, ref, 
        key AS datasource, 
        value AS freq_json 
        FROM variant, jsonb_each(frequencies)),

        freq_values AS (
        SELECT variant_id, 
        alt, ref,
        datasource, 
        key AS population_source_id, 
        value::numeric AS frequency 
        FROM freq_elements, jsonb_each(freq_json))

        SELECT p.datasource AS data_source, -- TODO: add version
        CASE WHEN frequency < 0.001 AND frequency > 0 THEN to_char(frequency, '9.9EEEE')
        WHEN frequency = 0 THEN 0::text
        ELSE round(frequency::numeric, 3)::text END AS frequency,
        v.alt AS allele,
        
        jsonb_build_object('abbreviation', abbreviation , 
        'population', display_value,
        'description', description) AS population
        
        FROM freq_values v, NIAGADS.Population p,
        normalize_alleles(v.ref, v.alt) n
        WHERE p.datasource = v.datasource 
        AND p.source_id = v.population_source_id
        ORDER BY data_source, description NULLS FIRST, abbreviation
    """,
    entity=Entity.VARIANT,
    bind_parameters=["id"],
)

VariantRecordQuery = QueryDefinition(
    query=f"""
    SELECT annotation FROM get_variant_primary_keys_and_annotations_tbl(:id, TRUE)
    """,
    bind_parameters=["id"],
    fetch_one=True,
    json_field="annotation",
    entity=Entity.VARIANT,
)


def get_association_counts(
    result: List[VariantAssociation],
) -> List[VariantAssociationSummary]:

    if len(result) == 0:  # FIXME: handle empty
        return []

    counts = {}
    ontology_terms = {}
    for r in result:
        # need to serialize to determine trait from phenotypes
        assoc = VariantAssociation(**r)

        category = getattr(assoc, "trait_category", None)
        trait = getattr(assoc, "trait", None)
        if trait == "None":
            # might happen due to join or unexpected phenotype
            raise RuntimeError(
                f"Error getting count summary: NULL value returned for a trait. {assoc}"
            )
        trait_name = str(trait)
        ontology_terms[trait_name] = (
            trait  # need mapping for after counts to generate summaries
        )

        counts.setdefault(category, {})
        counts[category][trait_name] = counts[category].get(trait_name, 0) + 1

    summaries = []
    for category, trait_dict in counts.items():
        for trait, numVariants in trait_dict.items():
            summaries.append(
                VariantAssociationSummary(
                    trait_category=category,
                    trait=ontology_terms[trait],
                    num_variants=numVariants,
                )
            )

    # Sort summaries by num_variants descending
    summaries.sort(key=lambda s: s.num_variants, reverse=True)
    return summaries


VariantAssociationsQuery = QueryDefinition(
    counts_func=get_association_counts,
    bind_parameters=[
        "association_source",
        "association_source",
        "id",
        "association_trait",
        "association_trait",
        "association_trait",
        "association_trait",
    ],
    allow_filters=True,
    query=f"""WITH Tracks AS ({GWAS_TRACK_CTE}),
        Results AS ({GWAS_RESULTS_CTE})
        SELECT * FROM Results
        {association_trait_FILTERS}
    """,
)


ColocatedVariantQuery = QueryDefinition(
    bind_parameters=["id"],
    query="""
        WITH variant AS (
            SELECT annotation->>'variant_id' AS variant_id,
            annotation->>'ref_snp_id' AS ref_snp_id,
            annotation->>'alt' AS alt_allele,
            annotation->>'ref' AS ref_allele,
            (annotation->>'bin_index')::ltree AS bin_index,
            (annotation->'location'->>'start')::int AS location_start,
            (annotation->'location'->>'start')::int + (annotation->'location'->>'length')::int - 1 AS location_end,
            annotation->'location'->>'chromosome' AS chromosome
            FROM get_variant_primary_keys_and_annotations_tbl(:id)
        ),

        cv AS (
            SELECT v.variant_id AS lookup_variant_id, v.ref_snp_id AS lookup_ref_snp_id, f.*
            FROM variant v JOIN LATERAL find_variants_by_range(v.chromosome, v.location_start, v.location_end) f ON TRUE
            WHERE v.variant_id != f.variant_id --exclude self
        ) 

        SELECT json_agg(variant_id) FILTER (WHERE lookup_ref_snp_id = annotation->>'ref_snp_id') AS alternative,
        json_agg(variant_id) FILTER (WHERE annotation->>'ref_snp_id' is NULL OR lookup_ref_snp_id != annotation->>'ref_snp_id') AS colocated_variants
        FROM cv
    """,
)
