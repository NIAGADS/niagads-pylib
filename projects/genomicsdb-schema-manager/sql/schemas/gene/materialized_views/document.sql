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
WITH genes AS (
    SELECT
        -- index fields
        g.gene_id,
        g.bin_index,
        g.chromosome,
        g.span,
        g.source_id,
        -- chunked document fields
        jsonb_build_object(
            'gene_symbol',
            g.gene_symbol,
            'gene_name',
            g.gene_name
        ) AS nomenclature,
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
            NULL
        ) AS location,
        jsonb_build_object('curie', ot.source_id, 'term', ot.term) AS classification,
        '{}' :: JSONB AS identifers,
        '{}' :: JSONB AS xrefs,
        '{}' :: JSONB AS publications,
        '{}' :: JSONB AS group_memberships,
        '{}' :: JSONB AS annotation
    FROM
        Gene.Gene g,
        Reference.OntologyTerm ot
    WHERE
        ot.ontology_term_id = g.gene_type_id
)
SELECT
    *
FROM
    genes;