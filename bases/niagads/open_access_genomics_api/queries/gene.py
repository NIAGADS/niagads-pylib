from niagads.open_access_api_common.models.core import Entity
from niagads.open_access_api_common.models.query import QueryDefinition

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


GeneRecordQuery = QueryDefinition(
    query=f"""WITH goa AS ({GO_ASSOCIATION_CTE}),
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
        annotation AS hgnc_annotation,
        goa.go_annotation,
        pathway.pathway_membership
        FROM CBIL.GeneAttributes ga
        LEFT OUTER JOIN goa ON ga.source_id = goa.id
        LEFT OUTER JOIN pathway on ga.source_id = pathway.id
        WHERE ga.source_id = (SELECT gene_lookup(:id))
    """,
    bindParameters=["id"],
    # fetchOne=True,
    entity=Entity.GENE,
)

GeneAssociationsTable = QueryDefinition(
    bindParameters=["id", "subset", "subset"],
    query="""WITH 
            id AS 
            (   SELECT 
                    (:id)::text AS source_id 
            ) 
            ,
            tracks AS 
            (   SELECT 
                    track_id,
                    name,
                    description,
                    provenance->>'accession' AS accession,
                    CASE 
                        WHEN subject_phenotypes->>'ethnicity' IS NULL 
                        THEN 'European' 
                        ELSE subject_phenotypes->>'ethnicity' 
                    END                                     AS ethnicity,
                    subject_phenotypes->>'biological_sex'   AS biological_sex,
                    subject_phenotypes->>'genotype'         AS genotype,
                    biosample_characteristics->>'tissue'    AS tissue,
                    biosample_characteristics->>'biomarker' AS biomarker,
                    experimental_design->>'covariates'      AS covariates,
                    subject_phenotypes->>'disease'          AS disease,
                    subject_phenotypes->>'neuropathology'   AS neuropathology
                FROM 
                    Metadata.Track
                WHERE 
                    feature_type = 'variant'
                AND experimental_design->>'data_category' = 'summary statistics' 
            ),
            filteredtracks AS (
            SELECT * FROM tracks
            WHERE (:subset = 'AD_ONLY' AND disease::text LIKE '%Alzh%')
            OR (:subset != 'AD_ONLY' AND disease::text NOT LIKE '%Alzh%')
            ),
            RESULT AS
            (   SELECT
                    id.source_id,
                    r.track,
                    jsonb_build_object( 'variant_id', r.metaseq_id, 'ref_snp_id', r.ref_snp_id, 'type',
                    r.display_attributes->>'variant_class_abbrev', 'is_adsp_variant', r.is_adsp_variant,
                    'most_severe_consequence', jsonb_build_object( 'consequence', 
                    most_severe_consequence(r.annotation ->'ADSP_MOST_SEVERE_CONSEQUENCE'), 'impact', 
                    r.annotation-> 'ADSP_MOST_SEVERE_CONSEQUENCE'->>'impact', 'is_coding',(r.annotation->
                    'ADSP_MOST_SEVERE_CONSEQUENCE'->>'consequence_is_coding')::bool, 'impacted_gene',
                    jsonb_build_object( 'id', r.annotation->'ADSP_MOST_SEVERE_CONSEQUENCE'->>'gene_id',
                    'gene_symbol', r.annotation->'ADSP_MOST_SEVERE_CONSEQUENCE'->>'gene_symbol' ) ) ) AS
                    variant,
                    CASE
                        WHEN r.position::bigint < ga.location_start
                        THEN 'upstream'
                        WHEN r.position::bigint > ga.location_end
                        THEN 'downstream'
                        ELSE 'in gene'
                    END                                            AS relative_position,
                    r.test_allele                                  AS allele,
                    TO_CHAR(r.pvalue_display::numeric, '9.99EEEE') AS pvalue,
                    neg_log10_pvalue,
                    t.*
                FROM 
                    id, 
                    NIAGADS.VariantGWASTopHits r, 
                    filteredtracks                     t, 
                    CBIL.GeneAttributes        ga
                WHERE 
                    id.source_id = ga.source_id
                AND ga.bin_index_100kb_flank @> r.bin_index
                AND int4range(ga.location_start - 100000, ga.location_end + 100000, '[]') @> r.position
                AND ga.chromosome = r.chromosome
                AND t.track_id = r.track 
            )
            SELECT 
            * 
            FROM 
            RESULT
            ORDER BY 
            neg_log10_pvalue DESC
    """,
)
