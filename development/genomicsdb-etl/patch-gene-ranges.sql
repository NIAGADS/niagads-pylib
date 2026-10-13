-- gene structure coordinates were wrong [start, end), instead of [start, end+1), but it looks like error was fixed in the code at later date.
-- this is one-off-patch

UPDATE gene.gene AS g
SET
    span = int4range(
        lower(g.span),
        upper(g.span) + 1,
        '[)'
    ),
    bin_index = (
        SELECT ib.bin_index
        FROM reference.intervalbin AS ib
        WHERE ib.chromosome = g.chromosome
          AND ib.span @> int4range(
              lower(g.span),
              upper(g.span) + 1,
              '[)'
          )
        ORDER BY nlevel(ib.bin_index) DESC
        LIMIT 1
    );

UPDATE gene.exon AS e
SET
    span = int4range(
        lower(e.span),
        upper(e.span) + 1,
        '[)'
    ),
    bin_index = (
        SELECT ib.bin_index
        FROM reference.intervalbin AS ib
        WHERE ib.chromosome = e.chromosome
          AND ib.span @> int4range(
              lower(e.span),
              upper(e.span) + 1,
              '[)'
          )
        ORDER BY nlevel(ib.bin_index) DESC
        LIMIT 1
    );
    

    UPDATE gene.transcript AS t
SET
    span = int4range(
        lower(t.span),
        upper(t.span) + 1,
        '[)'
    ),
    bin_index = (
        SELECT ib.bin_index
        FROM reference.intervalbin AS ib
        WHERE ib.chromosome = t.chromosome
          AND ib.span @> int4range(
              lower(t.span),
              upper(t.span) + 1,
              '[)'
          )
        ORDER BY nlevel(ib.bin_index) DESC
        LIMIT 1
    );