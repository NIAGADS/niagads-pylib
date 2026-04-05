WITH 
    agg_exons AS 
    (   SELECT
            transcript_id,
            jsonb_agg( jsonb_build_object( 'id', source_id, 'rank', RANK, 'location', 
            format_genomic_location(chromosome, span, strand) ) ORDER BY RANK ) AS exons
        FROM 
            Gene.Exon
        GROUP BY 
            transcript_id
    ) 
    ,
    agg_transcripts AS 
    (   SELECT
            t.gene_id,
            jsonb_agg(jsonb_strip_nulls( jsonb_build_object( 'id', t.source_id, 'name', t.name, 'location', 
            format_genomic_location(t.chromosome, t.span, t.strand) ) ) || 
            CASE
                WHEN t.is_canonical 
                THEN jsonb_build_object('is_canonical', t.is_canonical)
                ELSE '{}'::jsonb
            END || 
            CASE
                WHEN e.exons IS NOT NULL 
                THEN jsonb_build_object('exons', e.exons)
                ELSE '{}'::jsonb
            END ORDER BY lower(span), upper(span)) AS transcripts
        FROM 
            Gene.Transcript t
        LEFT JOIN 
            agg_exons e 
        ON 
            e.transcript_id = t.transcript_id
        GROUP BY gene_id
    )
SELECT 
    *
FROM 
    transcripts;