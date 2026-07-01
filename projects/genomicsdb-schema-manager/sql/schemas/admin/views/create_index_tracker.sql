/* VIEW for monitor progress of tuning index builds, including ETA */

CREATE OR REPLACE VIEW ADMIN.index_build_tracker AS (SELECT
    p.pid,
    a.datname,
    p.relid::regclass AS table_name,
    COALESCE(
    NULLIF(p.index_relid, 0)::regclass::text,
        substring(a.query FROM 'CREATE\s+INDEX\s+(?:CONCURRENTLY\s+)?(?:IF\s+NOT\s+EXISTS\s+)?("?[\w_]+"?(?:\."?[\w_]+"?)?)')
    ) AS index_name,
    --p.index_relid::regclass AS index_name,
    p.phase,

    p.blocks_done,
    p.blocks_total,
    round(100.0 * p.blocks_done / nullif(p.blocks_total, 0), 2) AS pct_blocks,

    p.tuples_done,
    p.tuples_total,
    round(100.0 * p.tuples_done / nullif(p.tuples_total, 0), 2) AS pct_tuples,

    now() - a.query_start AS elapsed,

    CASE
        WHEN p.blocks_done > 0 AND p.blocks_total > 0 THEN
            ((now() - a.query_start) / p.blocks_done) * (p.blocks_total - p.blocks_done)
        WHEN p.tuples_done > 0 AND p.tuples_total > 0 THEN
            ((now() - a.query_start) / p.tuples_done) * (p.tuples_total - p.tuples_done)
        ELSE NULL
    END AS eta_remaining,

    CASE
        WHEN p.blocks_done > 0 AND p.blocks_total > 0 THEN
            a.query_start + ((now() - a.query_start) / p.blocks_done) * p.blocks_total
        WHEN p.tuples_done > 0 AND p.tuples_total > 0 THEN
            a.query_start + ((now() - a.query_start) / p.tuples_done) * p.tuples_total
        ELSE NULL
    END AS estimated_finish_time

FROM pg_stat_progress_create_index p
JOIN pg_stat_activity a ON a.pid = p.pid);