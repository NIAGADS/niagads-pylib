from niagads.reference.chromosomes import Human
from pydantic import BaseModel

from api.models.base_models import QueryDefinition, SerializableModel

class IGVFeatureRegion(SerializableModel):
    chromosome: Human
    start: int
    end: int

IVGRegionQuery = QueryDefinition(
    name='region',
    query=""" 
        SELECT v.mapping->>'chromosome' AS chromosome, 
        (v.mapping->>'position')::int AS start, 
        (v.mapping->>'position')::int + (v.mapping->>'length')::int AS end
        FROM get_variant_primary_keys_and_annotations_tbl(:feature_id) v
        
        UNION ALL
        
        SELECT g.chromosome,
        g.location_start AS start,
        g.location_end AS end
        FROM CBIL.GeneAttributes g
        WHERE lower(g.gene_symbol) = lower(:feature_id)
        OR g.source_id = :feature_id
        OR g.annotation->>'entrez_id' = :feature_id
    """,
    resultType=IGVFeatureRegion,
    bindParameters=['feature_id']
)


