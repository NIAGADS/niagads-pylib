#!/usr/bin/env bash
set -uo pipefail

DOCKER_IMAGE="postgres:18"

PARENT_TABLE="variant.variant"
COLUMN="bin_index"

POOL_SIZE=6
MAINTENANCE_WORK_MEM="8GB"
MAX_PARALLEL_MAINTENANCE_WORKERS=3
MAX_PARALLEL_WORKERS=3

RESUME_FROM="${1:-}"
ERROR_LOG="variant_bin_index_build_errors.log"

DATABASE_URI_DOCKER="${DATABASE_URI/localhost/host.docker.internal}"
DATABASE_URI_DOCKER="${DATABASE_URI_DOCKER/127.0.0.1/host.docker.internal}"

: > "$ERROR_LOG"

docker_psql() {
  docker run --rm -i \
    --add-host=host.docker.internal:host-gateway \
    "$DOCKER_IMAGE" \
    psql "$DATABASE_URI_DOCKER" "$@"
}

echo "Discovering partitions for ${PARENT_TABLE}..."

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

echo "Found ${#PARTITIONS[@]} partitions."

wait_for_slot() {
  while (( $(jobs -rp | wc -l) >= POOL_SIZE )); do
    wait -n
  done
}

build_index() {
  local fqtn="$1"
  local schema="${fqtn%%.*}"
  local table="${fqtn##*.}"
  local idx="ix_${table}__${COLUMN}"
  local output
  local rc

  echo "START ${schema}.${idx}"

  output="$(
    docker run --rm -i \
      --add-host=host.docker.internal:host-gateway \
      "$DOCKER_IMAGE" \
      psql "$DATABASE_URI_DOCKER" -a -e \
        -c "SET maintenance_work_mem = '${MAINTENANCE_WORK_MEM}';" \
        -c "SET max_parallel_maintenance_workers = ${MAX_PARALLEL_MAINTENANCE_WORKERS};" \
        -c "SET max_parallel_workers = ${MAX_PARALLEL_WORKERS};" \
        -c "CREATE INDEX ${idx} ON ${schema}.${table} USING GIST (${COLUMN});" \
      2>&1
  )"
  rc=$?

  printf '%s\n' "$output"

  if (( rc != 0 )) || grep -qiE '(^ERROR:|^FATAL:|^PANIC:)' <<< "$output"; then
    {
      echo "---- failed: ${schema}.${idx} on ${schema}.${table} ----"
      printf '%s\n' "$output"
      echo
    } >> "$ERROR_LOG"

    echo "ERROR ${schema}.${idx}"
  else
    echo "DONE ${schema}.${idx}"
  fi
}

resume_seen=false
[[ -z "$RESUME_FROM" ]] && resume_seen=true

for fqtn in "${PARTITIONS[@]}"; do
  table="${fqtn##*.}"

  if [[ "$resume_seen" == false ]]; then
    if [[ "$fqtn" == "$RESUME_FROM" || "$table" == "$RESUME_FROM" ]]; then
      resume_seen=true
    else
      echo "SKIP ${fqtn}"
      continue
    fi
  fi

  wait_for_slot
  build_index "$fqtn" &
done

wait

echo "Done."