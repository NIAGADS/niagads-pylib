DROP MATERIALIZED VIEW IF EXISTS gene.documents_mv;
DROP MATERIALIZED VIEW IF EXISTS gene.agg_transcripts;
DROP MATERIALIZED VIEW IF EXISTS gene.agg_proteins;
DROP MATERIALIZED VIEW IF EXISTS gene.agg_exons;

-- Step 1: Aggregate exons by transcript
CREATE MATERIALIZED VIEW gene.agg_exons AS
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

-- Step 2: Index aggregated exons by transcript ID.
CREATE INDEX idx_agg_exons_transcript_id ON gene.agg_exons(transcript_id);

-- Step 3: Aggregate proteins by transcript
CREATE MATERIALIZED VIEW gene.agg_proteins AS
SELECT
    transcript_id,
    jsonb_agg(source_id) AS proteins
FROM
    Gene.Protein
GROUP BY
    transcript_id;

-- Step 4: Index aggregated proteins by transcript ID.
CREATE INDEX idx_agg_proteins_transcript_id ON gene.agg_proteins(transcript_id);

-- Step 5: Aggregate transcripts by gene, including exon and protein data.
CREATE MATERIALIZED VIEW gene.agg_transcripts AS
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
        END || CASE
            WHEN p.proteins IS NOT NULL THEN jsonb_build_object('proteins', p.proteins)
            ELSE '{}' :: jsonb
        END
        ORDER BY
            lower(span),
            UPPER(span)
    ) AS transcripts
FROM
    Gene.Transcript t
    LEFT JOIN gene.agg_exons e ON e.transcript_id = t.transcript_id
    LEFT JOIN gene.agg_proteins p ON p.transcript_id = t.transcript_id
GROUP BY
    gene_id;

-- Step 6: Index aggregated transcripts by gene ID.
CREATE INDEX idx_agg_transcripts_gene_id ON gene.agg_transcripts(gene_id);

-- Step 7: Build gene documents from temporary aggregates and metadata CTEs.

CREATE MATERIALIZED VIEW Gene.Documents_MV AS (
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
        gt.namespace AS aspect,
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
    aspect,
    jsonb_build_object(
        'term_id', term_id,
        'term', term,
        'evidence',
        jsonb_agg(DISTINCT evidence_code)
            FILTER (WHERE evidence_code IS NOT NULL)
    ) AS term
FROM annotations
GROUP BY gene_id, term_id, term, aspect),
goassociations AS (
    SELECT
        genes.gene_id,
        associations.goa
    FROM Gene.Gene genes
    LEFT JOIN (
        SELECT
            gene_id,
            jsonb_agg(aspect_terms) AS goa
        FROM (
            SELECT
                gene_id,
                aspect,
                jsonb_build_object(aspect, jsonb_agg(term)) AS aspect_terms
            FROM terms
            GROUP BY gene_id, aspect
        ) grouped_terms
        GROUP BY gene_id
    ) associations
        ON associations.gene_id = genes.gene_id
),

gene_lists AS (
    SELECT
        g.gene_id,
        jsonb_agg(
                jsonb_build_object(
                    'evidence_code',
                    jsonb_build_object(
                        'term',
                        eco.term,
                        'curie',
                        eco.source_id
                    ),
                    'qualifier',
                    ae.qualifiers,
                    'rank',
                    glm.rank
                )
            ORDER BY
                glm.rank,
                ae.annotation_evidence_id
                )
         FILTER (WHERE glm.gene_list_entry_id IS NOT NULL) AS gene_lists
    FROM
        Gene.Gene g
    LEFT JOIN Gene.GeneListMembership glm
        ON glm.gene_id = g.gene_id
    LEFT JOIN Admin.TableCatalog tc
        ON tc.name = 'genelistmembership'
    LEFT JOIN Admin.SchemaCatalog sc
        ON sc.schema_id = tc.schema_id
        AND sc.name = 'gene'
    LEFT JOIN Gene.AnnotationEvidence ae
        ON ae.table_id = tc.table_id
        AND ae.row_id = glm.gene_list_entry_id
    LEFT JOIN Reference.OntologyTerm eco
        ON eco.ontology_term_id = ae.evidence_code_id
    GROUP BY
        g.gene_id
),

genes AS (
    SELECT
        -- index fields
        g.gene_id,
        g.bin_index,
        g.chromosome,
        g.span,
        g.source_id,
        ot.term AS gene_type,
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
            'location',  format_genomic_location(g.chromosome, g.span, g.strand),
             'cytogenic_location', cloc.location,
            'transcripts',
            transcripts.transcripts
        ) AS gene_structure,    
        xrefs.xrefs AS xrefs,
        publications.pubmed_ids AS publications,
        NULLIF(jsonb_strip_nulls(jsonb_build_object('gene_families', gf.families,'pathways', pathways.pathways, 'curated_lists', gene_lists)), '{}'::JSONB) AS memberships,
        goassociations.goa AS functional_annotation
    FROM
        Gene.Gene g
        LEFT JOIN gene.agg_transcripts AS transcripts
            ON transcripts.gene_id = g.gene_id,
        Reference.OntologyTerm ot,
        cytogenic_location AS cloc,
        xrefs,
        publications,
        hgnc_gene_families AS gf,
        gene_lists,
        nomenclature,
        pathways,
        goassociations
    WHERE
        ot.ontology_term_id = g.gene_type_id
        AND cloc.gene_id = g.gene_id
        AND xrefs.gene_id = g.gene_id
        AND publications.gene_id = g.gene_id
        AND gf.gene_id = g.gene_id
        AND nomenclature.gene_id = g.gene_id
        AND pathways.gene_id = g.gene_id
        AND gene_lists.gene_id = g.gene_id
        AND goassociations.gene_id = g.gene_id
)
SELECT
    genes.*,
    known_ad.gene_id IS NOT NULL AS associated_with_known_ad_locus
FROM
    genes
LEFT JOIN (
    SELECT DISTINCT
        gene_id
    FROM Gene.KnownADGenes
) known_ad
    ON known_ad.gene_id = genes.gene_id
);

-- Step 8: Add query indexes to the gene document materialized view.
CREATE INDEX ix_gene_document_mv_gene_id
    ON Gene.Documents_MV (gene_id);

CREATE INDEX ix_gene_document_mv_source_id
    ON Gene.Documents_MV (source_id);

CREATE INDEX ix_gene_document_mv_gene_type
    ON Gene.Documents_MV (gene_type);

CREATE INDEX ix_gene_document_mv__bin_index
    ON Gene.Documents_MV USING GIST (bin_index);

CREATE INDEX ix_gene_document_mv__span
    ON Gene.Documents_MV USING GIST (span);

CREATE INDEX ix_gene_document_mv_associated_with_known_ad_locus
    ON Gene.Documents_MV (associated_with_known_ad_locus)
    WHERE associated_with_known_ad_locus IS TRUE;
