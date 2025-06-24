from niagads.open_access_api_common.models.core import Entity
from niagads.open_access_api_common.models.query import QueryDefinition


VariantRecordQuery = QueryDefinition(
    query=f"""
        SELECT 
        id.variant_id,
        v.details->>'ref_snp_id' AS ref_snp_id,
        v.details->>'metaseq_id' AS variant_id, 
        v.details->>'variant_class_abbrev' AS variant_class,
        split_part(v.details->>'metaseq_id', ':', 3) as ref,
        split_part(v.details->>'metaseq_id', ':', 4) as alt,
        jsonb_build_object(
            'chromosome', v.details->>'chromosome',
            'start', (v.details->>'position')::INT - 1,
            'end', (v.details->>'position')::INT - 1 + COALESCE((v.details->>'length')::int, length(split_part(v.details->>'metaseq_id', ':', 3))::int)) AS location,
        COALESCE((v.details->>'length')::int, length(split_part(v.details->>'metaseq_id', ':', 3))::int) AS length,
        COALESCE(adsp_qc_status(id.variant_id)::text, 'NA') AS adsp_qc_status,
        v.details->'cadd' AS cadd_score,
        v.adsp_qc,
        FROM (SELECT :id::text AS variant_id) id, get_variant_annotation(id.variant_id) v
    """,
    bindParameters=["id"],
    fetchOne=True,
    entity=Entity.VARIANT,
)
