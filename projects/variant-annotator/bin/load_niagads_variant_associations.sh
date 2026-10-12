#!/bin/bash

usage() {
    echo "Usage: $0 <collection_key> --batch-size N [--commit] [--embedding-force-cpu] [--max-parallel N]" >&2
    echo "  --commit                  Persist changes to the database" >&2
    echo "  --batch-size N            Number of records to buffer per commit" >&2
    echo "  --embedding-force-cpu    Run embedding generation on the CPU" >&2
    echo "  --max-parallel N          Maximum concurrent track loads (default: 4)" >&2
}

if [[ $# -eq 1 && ( "$1" == "--help" || "$1" == "-h" ) ]]; then
    usage
    exit 0
fi

if [[ $# -lt 1 ]]; then
    usage
    exit 1
fi

COLLECTION_KEY="$1"
shift
BATCH_SIZE=5000
COMMIT_ARG=
EMBEDDING_FORCE_CPU=false
MAX_PARALLEL=4

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
            EMBEDDING_FORCE_CPU=true
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

if [[ -z "$BATCH_SIZE" ]]; then
    echo "Error: --batch-size is required" >&2
    usage
    exit 1
fi

if [[ -z "${DATA_DIR:-}" || -z "${CONFIG_DIR:-}" ]]; then
    echo "Error: DATA_DIR and CONFIG_DIR must be set" >&2
    exit 1
fi

if [[ ! "$BATCH_SIZE" =~ ^[1-9][0-9]*$ || ! "$MAX_PARALLEL" =~ ^[1-9][0-9]*$ ]]; then
    echo "Error: --batch-size and --max-parallel must be positive integers" >&2
    exit 1
fi

TRACK_DATA_DIR="$DATA_DIR/tracks/$COLLECTION_KEY/data"
TRACK_METADATA_DIR="$CONFIG_DIR/tracks/NIAGADS/$COLLECTION_KEY/metadata"
LOG_DIR="${LOG_DIR:-$DATA_DIR/../logs}"
mkdir -p "$LOG_DIR"

if [[ ! -d "$TRACK_DATA_DIR" ]]; then
    echo "Error: data directory does not exist: $TRACK_DATA_DIR" >&2
    exit 1
fi

if [[ ! -d "$TRACK_METADATA_DIR" ]]; then
    echo "Error: metadata directory does not exist: $TRACK_METADATA_DIR" >&2
    exit 1
fi

# Rename p-value-only files so they can be selected as paired OA tracks.
for file in "$TRACK_DATA_DIR"/*STD_pvalue_only.tsv.gz; do
    [[ -e "$file" ]] || continue
    mv -- "$file" "${file%STD_pvalue_only.tsv.gz}STD_OA.tsv.gz"
done

mapfile -t OA_FILES < <(find "$TRACK_DATA_DIR" -maxdepth 1 -type f \
    -name "${COLLECTION_KEY}_*_STD_OA.tsv.gz" -printf '%f\n' | sort)

if [[ ${#OA_FILES[@]} -eq 0 ]]; then
    echo "Error: no ${COLLECTION_KEY}_*_STD_OA.tsv.gz files found in $TRACK_DATA_DIR" >&2
    exit 1
fi

load_track() {
    local oa_file="$1"
    local track_id="${oa_file#${COLLECTION_KEY}_}"
    track_id="${track_id%%_STD_OA.tsv.gz}"
    local metadata_file="$TRACK_METADATA_DIR/${COLLECTION_KEY}_${track_id}_STD_OA_metadata.json"
    local data_file="$TRACK_DATA_DIR/${COLLECTION_KEY}_${track_id}_STD.tsv.gz"
    local log_file="$LOG_DIR/load-${COLLECTION_KEY}_${track_id}.log"
    local embedding_batch_size=512
    local embedding_args=()

    if [[ "$EMBEDDING_FORCE_CPU" == true ]]; then
        embedding_batch_size=128
        embedding_args=(--embedding-force-cpu)
    fi

    [[ -f "$metadata_file" ]] || {
        echo "Missing metadata file for track $track_id: $metadata_file" >&2
        return 1
    }
    [[ -f "$data_file" ]] || {
        echo "Missing paired STD data file for track $track_id: $data_file" >&2
        return 1
    }

    echo "[$(date +'%Y-%m-%d %H:%M:%S')] Starting track $track_id"
    runpipe-plugin --plugin GWASTrackLoader --genome-build GRCh38 \
        --seqrepo-data-proxy "$DATA_DIR/shared/seqrepo/2024-12-20" \
        --xdbref 'NIAGADS-DSS|current' \
        --collection "$COLLECTION_KEY" \
        --metadata-file "$metadata_file" \
        --data-file "$data_file" \
        --log-path "$log_file" \
        --batch-size "$BATCH_SIZE" \
        --embedding-batch-size "$embedding_batch_size" \
        "${embedding_args[@]}" \
        $COMMIT_ARG
    echo "[$(date +'%Y-%m-%d %H:%M:%S')] Completed track $track_id"
}

export COLLECTION_KEY DATA_DIR TRACK_DATA_DIR TRACK_METADATA_DIR LOG_DIR
export BATCH_SIZE EMBEDDING_FORCE_CPU
export COMMIT_ARG
export -f load_track

if command -v parallel &> /dev/null; then
    printf '%s\n' "${OA_FILES[@]}" | parallel -j "$MAX_PARALLEL" load_track
else
    printf '%s\0' "${OA_FILES[@]}" |
        xargs -0 -P "$MAX_PARALLEL" -I {} bash -c 'load_track "$@"' _ {}
fi
