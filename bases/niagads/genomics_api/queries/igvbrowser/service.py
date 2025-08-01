from niagads.api_common.models.services.query import QueryDefinition


IGVFeatureLookupQuery = QueryDefinition(
    query=""" 
        SELECT v.annotation->>'chromosome' AS chromosome, 
        (v.annotation->>'position')::int AS start, 
        (v.annotation->>'position')::int + (v.annotation->>'length')::int AS end
        FROM get_variant_primary_keys_and_annotations_tbl(:id) v
        
        UNION ALL
        
        SELECT g.chromosome,
        g.location_start AS start,
        g.location_end AS end
        FROM CBIL.GeneAttributes g
        WHERE upper(g.gene_symbol) = upper(:id)
        OR g.source_id = :id
        OR g.annotation->>'entrez_id' = :id
        
        ORDER BY chromosome NULLS LAST LIMIT 1
    """,
    bind_parameters=["id"],
    fetch_one=True,
)
