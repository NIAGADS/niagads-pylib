from niagads.open_access_api_common.models.records.core import Entity
from niagads.open_access_api_common.models.services.query import QueryDefinition
from niagads.open_access_genomics_api.queries.associations import (
    GWAS_COMMON_FIELDS,
    GWAS_TRACK_CTE,
    GWAS_TRAIT_FILTERS,
)

GO_ASSOCIATION_CTE = """
    SELECT ga.source_id AS id, 
        json_agg(jsonb_build_object(
            'go_term_id', ot.source_id, 
            'go_term', ot.name, 'evidence', goa.evidence, 
            'ontology', CASE ontology.name
                WHEN 'molecular_function' THEN 'MF'
                WHEN 'cellular_component' THEN 'CC'
                WHEN 'biological_process' THEN 'BP'  
                END)
        ) AS go_annotation
    FROM CBIL.GeneAttributes ga,
    CBIL.GoAssociation goa,
    SREs.OntologyTerm ot,
    SRES.OntologyTerm ontology
    WHERE goa.gene_id = ga.gene_id
    AND go_term_id = ot.ontology_term_id
    AND ot.ancestor_term_id = ontology.ontology_term_id
    GROUP BY id 
"""

PATHWAY_CTE = """
    SELECT ga.source_id AS id, 
        json_agg(jsonb_build_object(
            'pathway', p.name, 
            'pathway_id', p.source_id, 
            'pathway_source', xdbr.id_type)) AS pathway_membership
    FROM CBIL.GeneAttributes ga,
    SREs.Pathway p,
    SREs.PathwayNode pn,
    SRes.ExternalDatabaseRelease xdbr
    WHERE p.pathway_id  = pn.pathway_id
    AND pn.row_id = ga.gene_id
    AND xdbr.external_database_release_id = p.external_database_release_id
    GROUP BY id
"""

GENE_RECORD_QUERY = f"""WITH goa AS ({GO_ASSOCIATION_CTE}),
        pathway AS ({PATHWAY_CTE})
        SELECT source_id AS id, 
        gene_symbol,
        annotation->>'name' AS gene_name,
        to_json(string_to_array(annotation->>'prev_symbol', '|') 
            || string_to_array(annotation->>'alias_symbol', '|')) AS synonyms,
        gene_type,
        jsonb_build_object(
            'chromosome', chromosome, 
            'start', location_start, 
            'end', location_end,
            'strand', CASE WHEN is_reversed THEN '-' ELSE '+' END
        ) AS location,
        annotation AS nomenclature,
        goa.go_annotation,
        pathway.pathway_membership
        FROM CBIL.GeneAttributes ga
        LEFT OUTER JOIN goa ON ga.source_id = goa.id
        LEFT OUTER JOIN pathway on ga.source_id = pathway.id
        WHERE ga.source_id = (SELECT gene_lookup(:id))
    """


GWAS_RESULTS_CTE = f"""
    SELECT 
    {GWAS_COMMON_FIELDS},
    CASE
        WHEN r.position::bigint < ga.location_start
        THEN 'upstream'
        WHEN r.position::bigint > ga.location_end
        THEN 'downstream'
        ELSE 'in gene'
    END AS relative_position
    FROM NIAGADS.VariantGWASTopHits r, Tracks t, CBIL.GeneAttributes ga
    WHERE ga.source_id = (SELECT gene_lookup(:id))
    AND ga.bin_index_100kb_flank @> r.bin_index
    AND int4range(ga.location_start - 100000, ga.location_end + 100000, '[]') @> r.position
    AND ga.chromosome = r.chromosome
    AND t.track_id = r.track 
    ORDER BY neg_log10_pvalue DESC
"""


GeneRecordQuery = QueryDefinition(
    query=GENE_RECORD_QUERY, bindParameters=["id"], entity=Entity.GENE, fetchOne=True
)

GeneFunctionQuery = QueryDefinition(
    query=GENE_RECORD_QUERY,
    bindParameters=["id"],
    jsonField="go_annotation",
    fetchOne=True,
)

GenePathwayQuery = QueryDefinition(
    query=GENE_RECORD_QUERY,
    bindParameters=["id"],
    jsonField="pathway_membership",
    fetchOne=True,
)


GeneAssociationsQuery = QueryDefinition(
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
