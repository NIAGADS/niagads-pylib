/*
 -- Module: create_relation_size_trackers.sql
 -- Description: SQL view definitions for tracking relation and table sizes.
 */
CREATE
OR REPLACE VIEW admin.top_relations_by_size (relation, SIZE) AS
SELECT
    (
        ((n.nspname) :: text || '.' :: text) || (c.relname) :: text
    ) AS relation,
    pg_size_pretty(pg_relation_size((c.oid) :: regclass)) AS SIZE
FROM
    (
        pg_class c
        LEFT JOIN pg_namespace n ON ((n.oid = c.relnamespace))
    )
WHERE
    (
        n.nspname <> ALL (
            ARRAY ['pg_catalog'::name, 'information_schema'::name]
        )
    )
ORDER BY
    (pg_relation_size((c.oid) :: regclass)) DESC
LIMIT
    50;

CREATE
OR REPLACE VIEW admin.top_tables_by_size (relation, total_size) AS
SELECT
    (
        ((n.nspname) :: text || '.' :: text) || (c.relname) :: text
    ) AS relation,
    pg_size_pretty(pg_total_relation_size((c.oid) :: regclass)) AS total_size
FROM
    (
        pg_class c
        LEFT JOIN pg_namespace n ON ((n.oid = c.relnamespace))
    )
WHERE
    (
        (
            n.nspname <> ALL (
                ARRAY ['pg_catalog'::name, 'information_schema'::name]
            )
        )
        AND (c.relkind <> 'i' :: "char")
        AND (n.nspname !~ '^pg_toast' :: text)
    )
ORDER BY
    (pg_total_relation_size((c.oid) :: regclass)) DESC
LIMIT
    50;