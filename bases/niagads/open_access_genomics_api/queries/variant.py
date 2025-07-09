from niagads.open_access_api_common.models.records.core import Entity
from niagads.open_access_api_common.models.services.query import QueryDefinition
from niagads.open_access_genomics_api.queries.associations import (
    GWAS_COMMON_FIELDS,
    GWAS_TRACK_CTE,
    GWAS_TRAIT_FILTERS,
)


GWAS_RESULTS_CTE = f"""
    SELECT 
    {GWAS_COMMON_FIELDS}
    FROM NIAGADS.VariantGWASTopHits r, Tracks t
    WHERE t.track_id = r.track 
    AND r.metaseq_id = (SELECT find_variant_primary_key(:id))
    ORDER BY neg_log10_pvalue DESC
"""


VariantRecordQuery = QueryDefinition(
    query=f"""
    SELECT annotation FROM get_variant_primary_keys_and_annotations_tbl(:id, TRUE)
    """,
    bindParameters=["id"],
    fetchOne=True,
    jsonField="annotation",
    entity=Entity.VARIANT,
)


VariantssociationsQuery = QueryDefinition(
    bindParameters=[
        "gwas_source",
        "gwas_source",
        "id",
        "gwas_trait",
        "gwas_trait",
        "gwas_trait",
        "gwas_trait",
    ],
    allowFilters=True,
    query=f"""WITH Tracks AS ({GWAS_TRACK_CTE}),
        Results AS ({GWAS_RESULTS_CTE})
        SELECT * FROM Results
        {GWAS_TRAIT_FILTERS}
    """,
)
