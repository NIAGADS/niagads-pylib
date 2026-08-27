-- Step 1: Create agg_exons as a temp table
CREATE TEMP TABLE agg_exons AS
SELECT
    transcript_id,
    jsonb_agg(
        jsonb_build_object(
            'id',
            source_id,
            'rank',
            RANK,
            'location',
            format_genomic_location(chromosome, span, strand)
        )
        ORDER BY
            RANK
    ) AS exons
FROM
    Gene.Exon
GROUP BY
    transcript_id;

-- Step 2: Add indexes to agg_exons if needed
CREATE INDEX idx_agg_exons_transcript_id ON agg_exons(transcript_id);

-- Step 3: Create agg_transcripts as a temp table
CREATE TEMP TABLE agg_transcripts AS
SELECT
    t.gene_id,
    jsonb_agg(
        jsonb_strip_nulls(
            jsonb_build_object(
                'id',
                t.source_id,
                'name',
                t.name,
                'location',
                format_genomic_location(t.chromosome, t.span, t.strand)
            )
        ) || CASE
            WHEN t.is_canonical THEN jsonb_build_object('is_canonical', t.is_canonical)
            ELSE '{}' :: jsonb
        END || CASE
            WHEN e.exons IS NOT NULL THEN jsonb_build_object('exons', e.exons)
            ELSE '{}' :: jsonb
        END
        ORDER BY
            lower(span),
            UPPER(span)
    ) AS transcripts
FROM
    Gene.Transcript t
    LEFT JOIN agg_exons e ON e.transcript_id = t.transcript_id
GROUP BY
    gene_id;

-- Step 4: Add indexes to agg_transcripts if needed
CREATE INDEX idx_agg_transcripts_gene_id ON agg_transcripts(gene_id);

-- Step 5: Use the temp tables in your main query
WITH cytogenic_location AS (
SELECT
    g.gene_id,
    x.xref_value AS location
FROM Gene.Gene g
LEFT JOIN Gene.XRef x
    ON x.gene_id = g.gene_id
    AND x.xref_label = 'location'
),
xrefs AS (
SELECT g.gene_id, 
   COALESCE(
            jsonb_object_agg(x.xref_label, x.xref_value)
                FILTER (WHERE x.xref_label IS NOT NULL), -- needed b/c left join could leave label and value null
            NULL
        ) AS xrefs
FROM Gene.Gene g
LEFT JOIN Gene.XRef x
    ON x.gene_id = g.gene_id
    AND x.xref_category = 'IDENTIFIER' GROUP BY g.gene_id
),
publications AS (
SELECT g.gene_id, 
   COALESCE(
           jsonb_agg(x.xref_value)
                FILTER (WHERE x.xref_value IS NOT  NULL), -- needed b/c left join could leave value null
            NULL
        ) AS pubmed_ids
FROM Gene.Gene g
LEFT JOIN Gene.XRef x
    ON x.gene_id = g.gene_id
    AND x.xref_category = 'PUBLICATION' GROUP BY g.gene_id
),
hgnc_gene_families AS (
SELECT g.gene_id, 
   CASE WHEN COUNT(x.xref_value) = 0 THEN NULL
   ELSE
   jsonb_build_object('HGNC', COALESCE(
            jsonb_agg(x.xref_value)
                FILTER (WHERE x.xref_value IS NOT  NULL), -- needed b/c left join could leave label and value null
            NULL
        )) END AS families
FROM Gene.Gene g
LEFT JOIN Gene.XRef x
    ON x.gene_id = g.gene_id
    AND x.xref_category = 'GROUP_MEMBERSHIP' 
    AND x.xref_label = 'gene_group'
    GROUP BY g.gene_id
),
nomenclature AS (
SELECT g.gene_id,
   COALESCE(
            jsonb_agg(x.xref_value)
                FILTER (WHERE x.xref_value IS NOT  NULL), -- needed b/c left join could leave label and value null
            NULL
        ) AS synonyms
FROM Gene.Gene g
LEFT JOIN Gene.XRef x
    ON x.gene_id = g.gene_id
    AND x.xref_category = 'NOMENCLATURE' 
    AND x.xref_label IN ('alias_symbol', 'pre_symbol')
    GROUP BY g.gene_id
),
pathways AS 
(SELECT
    g.gene_id,
    json_agg(
        jsonb_build_object(
            'pathway_name', p.name,
            'pathway_id', p.source_id,
            'data_source', d.database_key
        )
    ) FILTER (WHERE p.pathway_id IS NOT NULL) AS pathways
FROM Gene.Gene g
LEFT JOIN Gene.PathwayMembership pm
    ON pm.gene_id = g.gene_id
LEFT JOIN Reference.Pathway p
    ON p.pathway_id = pm.pathway_id
LEFT JOIN Reference.ExternalDatabase d
    ON d.external_database_id = p.external_database_id
GROUP BY g.gene_id),
annotations AS (
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

genes AS (
    SELECT
        -- index fields
        g.gene_id,
        g.bin_index,
        g.chromosome,
        g.span,
        g.source_id,
        -- chunked document fields
        jsonb_strip_nulls(
        jsonb_build_object(
            'gene_symbol',
            g.gene_symbol,
            'gene_name',
            g.gene_name,
            'synonyms', nomenclature.synonyms
        )) AS nomenclature,
        jsonb_build_object(
            'genomic_location',
            jsonb_build_object(
                'chromosome',
                g.chromosome,
                'span',
                g.span,
                'strand',
                g.strand
            ),
            'cytogenic_location',
            cloc.location
        ) AS location,
        jsonb_build_object('curie', ot.source_id, 'term', ot.term) AS classification,
        xrefs.xrefs AS xrefs,
        publications.pubmed_ids AS publications,
        NULLIF(jsonb_strip_nulls(jsonb_build_object('gene_families', gf.families,'cuated_targets', NULL, 'pathways', pathways.pathways)), '{}'::JSONB) AS memberships,
        '{}' :: JSONB AS annotation
    FROM
        Gene.Gene g,
        Reference.OntologyTerm ot,
        cytogenic_location AS cloc,
        xrefs,
        publications,
        hgnc_gene_families AS gf,
        nomenclature,
        pathways
    WHERE
        ot.ontology_term_id = g.gene_type_id
        AND cloc.gene_id = g.gene_id
        AND xrefs.gene_id = g.gene_id
        AND publications.gene_id = g.gene_id
        AND gf.gene_id = g.gene_id
        AND nomenclature.gene_id = g.gene_id
        AND pathways.gene_id = g.gene_id
)
SELECT
    *
FROM
    genes;