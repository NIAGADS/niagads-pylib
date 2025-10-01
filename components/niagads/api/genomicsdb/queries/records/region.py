from niagads.api.common.config import Settings
from niagads.api.common.models.records import Entity
from niagads.api.common.models.services.query import QueryDefinition

REGION_RECORD_QUERY = f"""
SELECT :id AS id, 'gene' AS feature_type, num_genes AS num_features, 
range_relation, gene_type AS feature_subtype 
FROM summarize_genes_by_range(:chromosome, :start, :end)
UNION ALL 
SELECT :id AS id, CASE WHEN variant_type LIKE 'SV_%' THEN 'structural_variant' ELSE 'small_variant' END AS feature_type,
num_variants AS num_features, range_relation, variant_type AS feature_subtype 
FROM summarize_variants_by_range(:chromosome, :start, :end, :end-:start>{Settings.from_env().MAX_SPAN_SIZE}) 
ORDER BY feature_type, num_features DESC
"""

# REGION_GENE_QUERY =

# STRUCTURAL_VARIANT_QUERY = SELECT * FROM sv_by_range_lookup(:chromosome, :start, :end)

RegionVariantQuery = QueryDefinition(
    query="SELECT * FROM variants_by_range_lookup(:chromosome, :start, :end) UNION ALL SELECT * FROM sv_by_range_lookup(:chromosome, :start, :end)",
    bind_parameters=["chromosome", "start", "end"],
    fetch_one=False,
)

RegionStructuralVariantQuery = QueryDefinition(
    query="SELECT * FROM sv_by_range_lookup(:chromosome, :start, :end)",
    bind_parameters=["chromosome", "start", "end"],
    fetch_one=False,
)

RegionGeneQuery = QueryDefinition(
    query="SELECT * FROM genes_by_range_lookup(:chromosome, :start, :end)",
    bind_parameters=["chromosome", "start", "end"],
    fetch_one=False,
)


RegionRecordQuery = QueryDefinition(
    query=REGION_RECORD_QUERY,
    bind_parameters=[
        "id",
        "chromosome",
        "start",
        "end",
        "id",
        "chromosome",
        "start",
        "end",
        "end",
        "start",
    ],
    use_id_select_wrapper=True,
    entity=Entity.REGION,
    fetch_one=False,
)
