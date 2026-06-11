#!/usr/bin/env bash
set -uo pipefail

DOCKER_IMAGE="postgres:18"
PARENT_TABLE="variant.variant"
COLUMN="bin_index"
BATCH_SIZE=3
MAINTENANCE_WORK_MEM="16GB"
ERROR_LOG="variant_bin_index_build_errors.log"

: > "$ERROR_LOG"

docker_psql() {
  docker run --rm -i \
    --network host \
    "$DOCKER_IMAGE" \
    psql "$DATABASE_URI" "$@"
}

mapfile -t PARTITIONS < <(
  docker_psql -Atq <<SQL
SELECT pn.nspname || '.' || pc.relname
FROM pg_inherits i
JOIN pg_class pc ON pc.oid = i.inhrelid
JOIN pg_namespace pn ON pn.oid = pc.relnamespace
WHERE i.inhparent = '${PARENT_TABLE}'::regclass
ORDER BY pc.relname;
SQL
)

for ((i = 0; i < ${#PARTITIONS[@]}; i += BATCH_SIZE)); do
  batch=( "${PARTITIONS[@]:i:BATCH_SIZE}" )

  output="$(
    {
      echo "SET maintenance_work_mem = '${MAINTENANCE_WORK_MEM}';"
      echo

      for fqtn in "${batch[@]}"; do
        schema="${fqtn%%.*}"
        table="${fqtn##*.}"
        idx="ix_${table}__${COLUMN}"

        echo "\\echo Building ${schema}.${idx} on ${schema}.${table}"
        echo "CREATE INDEX CONCURRENTLY IF NOT EXISTS ${idx}"
        echo "ON ${schema}.${table} USING GIST (${COLUMN});"
        echo
      done
    } | docker_psql -a -e -f - 2>&1
  )"

  printf '%s\n' "$output"

  if grep -qiE '(^ERROR:|^FATAL:|^PANIC:)' <<< "$output"; then
    {
      echo "---- batch failed: ${batch[*]} ----"
      printf '%s\n' "$output"
      echo
    } >> "$ERROR_LOG"
  fi
done