/*
 -- Module: create_lock_monitor.sql
 -- Description: SQL view for monitoring database locks.
 */
CREATE
OR REPLACE VIEW admin.lock_monitor (
    blocked_pid,
    blocked_user,
    blocking_pid,
    blocking_user,
    blocked_statement,
    current_statement_in_blocking_process,
    blocked_application,
    blocking_application
) AS
SELECT
    blocked_locks.pid AS blocked_pid,
    blocked_activity.usename AS blocked_user,
    blocking_locks.pid AS blocking_pid,
    blocking_activity.usename AS blocking_user,
    blocked_activity.query AS blocked_statement,
    blocking_activity.query AS current_statement_in_blocking_process,
    blocked_activity.application_name AS blocked_application,
    blocking_activity.application_name AS blocking_application
FROM
    (
        (
            (
                pg_locks blocked_locks
                JOIN pg_stat_activity blocked_activity ON (
                    (
                        blocked_activity.pid = blocked_locks.pid
                    )
                )
            )
            JOIN pg_locks blocking_locks ON (
                (
                    (
                        blocking_locks.locktype = blocked_locks.locktype
                    )
                    AND (
                        NOT (
                            blocking_locks.database IS DISTINCT
                            FROM
                                blocked_locks.database
                        )
                    )
                    AND (
                        NOT (
                            blocking_locks.relation IS DISTINCT
                            FROM
                                blocked_locks.relation
                        )
                    )
                    AND (
                        NOT (
                            blocking_locks.page IS DISTINCT
                            FROM
                                blocked_locks.page
                        )
                    )
                    AND (
                        NOT (
                            blocking_locks.tuple IS DISTINCT
                            FROM
                                blocked_locks.tuple
                        )
                    )
                    AND (
                        NOT (
                            blocking_locks.virtualxid IS DISTINCT
                            FROM
                                blocked_locks.virtualxid
                        )
                    )
                    AND (
                        NOT (
                            blocking_locks.transactionid IS DISTINCT
                            FROM
                                blocked_locks.transactionid
                        )
                    )
                    AND (
                        NOT (
                            blocking_locks.classid IS DISTINCT
                            FROM
                                blocked_locks.classid
                        )
                    )
                    AND (
                        NOT (
                            blocking_locks.objid IS DISTINCT
                            FROM
                                blocked_locks.objid
                        )
                    )
                    AND (
                        NOT (
                            blocking_locks.objsubid IS DISTINCT
                            FROM
                                blocked_locks.objsubid
                        )
                    )
                    AND (
                        blocking_locks.pid <> blocked_locks.pid
                    )
                )
            )
        )
        JOIN pg_stat_activity blocking_activity ON (
            (
                blocking_activity.pid = blocking_locks.pid
            )
        )
    )
WHERE
    (NOT blocked_locks.granted);