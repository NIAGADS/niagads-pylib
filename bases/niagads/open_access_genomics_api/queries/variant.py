from niagads.open_access_api_common.models.core import Entity
from niagads.open_access_api_common.models.query import QueryDefinition


VariantRecordQuery = QueryDefinition(
    query=f"""
    SELECT annotation FROM get_variant_primary_keys_and_annotations_tbl(:id, TRUE);
    """,
    bindParameters=["id"],
    fetchOne=True,
    jsonField="annotation",
    entity=Entity.VARIANT,
)
