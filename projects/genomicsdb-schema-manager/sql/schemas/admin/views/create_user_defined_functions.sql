/*
 -- Module: create_user_defined_functions.sql
 -- Description: SQL view for listing user-defined functions.
 */
CREATE
OR REPLACE VIEW admin.user_defined_functions AS (
    SELECT
        *
    FROM
        (
            SELECT
                n.nspname AS function_schema,
                p.proname AS function_name,
                l.lanname AS function_language,
                CASE
                    WHEN l.lanname = 'internal' THEN p.prosrc
                    ELSE pg_get_functiondef(p.oid)
                END AS definition,
                pg_get_function_arguments(p.oid) AS function_arguments,
                t.typname AS return_type
            FROM
                pg_proc p
                LEFT JOIN pg_namespace n ON p.pronamespace = n.oid
                LEFT JOIN pg_language l ON p.prolang = l.oid
                LEFT JOIN pg_type t ON t.oid = p.prorettype
            WHERE
                n.nspname NOT IN ('pg_catalog', 'information_schema')
            ORDER BY
                function_schema,
                function_name
        ) a
    WHERE
        function_language != 'c'
);