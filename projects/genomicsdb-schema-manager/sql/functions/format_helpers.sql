--
-- format_genomic_location
--   Formats a genomic location as "chrom:start-end:strand" (e.g., chr1:100-200:+).
--   Args:
--     chromosome (HumanGenome): Chromosome name (with or without 'chr' prefix)
--     span (INT4RANGE): Genomic interval (start/end)
--     strand (TEXT): Strand symbol ('+', '-', or '.')
--   Returns:
--     text: Formatted genomic location string
--
DROP FUNCTION IF EXISTS format_genomic_location(HumanGenome, INT4RANGE, TEXT);
CREATE OR REPLACE FUNCTION format_genomic_location(chromosome HumanGenome, span INT4RANGE, strand TEXT)
    RETURNS text
    LANGUAGE sql
    IMMUTABLE
    AS $$
        SELECT concat_ws(':',
            replace(chromosome::text, 'chr', ''),
            lower(span) || '-' || upper(span) - 1, --everything in the db should be inclusive end, 1-based
            CASE WHEN strand = '-' THEN strand ELSE NULL END
        )
    $$;