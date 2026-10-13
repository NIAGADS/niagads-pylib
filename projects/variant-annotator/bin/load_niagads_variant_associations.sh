#!/bin/bash

usage() {
    echo "Usage: $0 <collection_key> --batch-size N [--commit] [--embedding-force-cpu] [--max-parallel N]" >&2
    echo "  --commit                  Persist changes to the database" >&2
    echo "  --batch-size N            Number of records to buffer per commit" >&2
    echo "  --embedding-force-cpu    Run embedding generation on the CPU" >&2
    echo "  --max-parallel N          Maximum concurrent track loads (default: 4)" >&2
}

COLLECTION_KEY="$1"
shift
BATCH_SIZE=5000
COMMIT_ARG=
EMBEDDING_BATCH_SIZE=512
EMBEDDING_FORCE_CPU_ARG=
MAX_PARALLEL=4
ZERO_BASED=

while [[ $# -gt 0 ]]; do
    case "$1" in
        --batch-size)
            [[ $# -ge 2 ]] || { echo "Error: --batch-size requires a value" >&2; exit 1; }
            BATCH_SIZE="$2"
            shift 2
            ;;
        --commit)
            COMMIT_ARG=--commit
            shift
            ;;
        --embedding-force-cpu)
            EMBEDDING_BATCH_SIZE=128
            EMBEDDING_FORCE_CPU_ARG=--embedding-force-cpu
            shift
            ;;
        --is-zero-based)
            IS_ZERO_BASED_ARG=--is-zero-based
            shift
            ;;
        --max-parallel)
            [[ $# -ge 2 ]] || { echo "Error: --max-parallel requires a value" >&2; exit 1; }
            MAX_PARALLEL="$2"
            shift 2
            ;;
        --help|-h)
            usage
            exit 0
            ;;
        *)
            echo "Error: unknown argument: $1" >&2
            usage
            exit 1
            ;;
    esac
done

TRACK_DATA_DIR="$DATA_DIR/tracks/$COLLECTION_KEY/data"
TRACK_METADATA_DIR="$CONFIG_DIR/tracks/NIAGADS/$COLLECTION_KEY/metadata"
LOG_DIR="${LOG_DIR:-$DATA_DIR/../logs}"
mkdir -p "$LOG_DIR"

# Rename p-value-only files so they can be selected as paired OA tracks.
for file in "$TRACK_DATA_DIR"/*STD_pvalue_only.tsv.gz; do
    [[ -e "$file" ]] || continue
    mv -- "$file" "${file%STD_pvalue_only.tsv.gz}STD_OA.tsv.gz"
done

mapfile -t TRACK_IDS < <(
    find "$TRACK_DATA_DIR" -maxdepth 1 -type f \
        -name "${COLLECTION_KEY}_*_STD_OA.tsv.gz" -printf '%f\n' |
        cut -d_ -f2 |
        sed 's/_STD_OA.tsv.gz$//' |
        sort -u
)

load_track() {
    local track_id="$1"
    local metadata_file="$TRACK_METADATA_DIR/${COLLECTION_KEY}_${track_id}_STD_OA_metadata.json"
    local data_file="$TRACK_DATA_DIR/${COLLECTION_KEY}_${track_id}_STD.tsv.gz"
    local log_file="$LOG_DIR/load-${COLLECTION_KEY}_${track_id}.log"
    echo "[$(date +'%Y-%m-%d %H:%M:%S')] Starting track $track_id"
    runpipe-plugin --plugin GWASTrackLoader --genome-build GRCh38 \
        --seqrepo-data-proxy "$DATA_DIR/shared/seqrepo/2024-12-20" \
        --xdbref 'NIAGADS-DSS|current' \
        --collection "$COLLECTION_KEY" \
        --metadata-file "$metadata_file" \
        --data-file "$data_file" \
        --log-path "$log_file" \
        --batch-size "$BATCH_SIZE" \
        --embedding-batch-size "$EMBEDDING_BATCH_SIZE" \
        $EMBEDDING_FORCE_CPU_ARG \
        $IS_ZERO_BASED_ARG \
        $COMMIT_ARG
    echo "[$(date +'%Y-%m-%d %H:%M:%S')] Completed track $track_id"
}

export COLLECTION_KEY DATA_DIR TRACK_DATA_DIR TRACK_METADATA_DIR LOG_DIR
export BATCH_SIZE EMBEDDING_BATCH_SIZE EMBEDDING_FORCE_CPU_ARG IS_ZERO_BASED_ARG
export COMMIT_ARG
export -f load_track

if command -v parallel &> /dev/null; then
    printf '%s\n' "${TRACK_IDS[@]}" | parallel -j "$MAX_PARALLEL" load_track
else
    printf '%s\0' "${TRACK_IDS[@]}" |
        xargs -0 -P "$MAX_PARALLEL" -I {} bash -c 'load_track "$@"' _ {}
fi
