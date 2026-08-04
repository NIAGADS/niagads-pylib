
WITH annotations AS (
    SELECT
        g.gene_id,
        gt.source_id AS term_id,
        gt.term,
        UPPER(
    array_to_string(
        ARRAY(
            SELECT LEFT(word, 1)
            FROM UNNEST(string_to_array(gt.namespace, '_')) AS word
        ), '')) AS aspect,
        (
            SELECT value
            FROM unnest(eco.synonyms) AS value
            WHERE value ~ '^[A-Z]{3}$'
            LIMIT 1
        ) AS evidence_code
    FROM Gene.AnnotationEvidence ae
    JOIN Admin.TableCatalog tc
        ON tc.table_id = ae.table_id
        AND tc.name = 'goassociation'
    JOIN Gene.GoAssociation goa
        ON goa.go_association_id = ae.row_id
    JOIN Reference.OntologyTerm eco
        ON eco.ontology_term_id = ae.evidence_code_id
    JOIN Reference.OntologyTerm gt
        ON gt.ontology_term_id = goa.go_term_id
    JOIN Gene.Gene g
        ON g.gene_id = goa.gene_id
), 
terms AS (
SELECT
    gene_id,
    jsonb_build_object(
        'term_id', term_id,
        'term', term,
        'aspect', aspect,
        'evidence',
        jsonb_agg(DISTINCT evidence_code)
            FILTER (WHERE evidence_code IS NOT NULL)
    ) AS term
FROM annotations
GROUP BY gene_id, term_id, term, aspect),
goassociations AS (
SELECT gene_id, jsonb_agg(term) 
FROM 
terms GROUP BY gene_id)
SELECT * FROM goassociations;