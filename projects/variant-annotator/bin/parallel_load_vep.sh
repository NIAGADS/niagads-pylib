#!/bin/bash

usage() {
    echo "Usage: $0 --vep-result-dir DIR [--num-parallel N] [--batch-size N] [--embedding-batch-size N] [--embedding-force-cpu] [--is-chr-combined] [--commit] [--debug]" >&2
}

BATCH_SIZE=50000
VEP_RESULT_DIR=
NUM_PARALLEL=4
EMBEDDING_BATCH_SIZE=1024
COMMIT_ARG=
DEBUG_ARG=
IS_CHR_COMBINED_ARG=
EMBEDDING_FORCE_CPU_ARG=

while [[ $# -gt 0 ]]; do
    case "$1" in
        --vep-result-dir)
            VEP_RESULT_DIR="$2"
            shift 2
            ;;
        --num-parallel)
            NUM_PARALLEL="$2"
            shift 2
            ;;
        --batch-size)
            BATCH_SIZE="$2"
            shift 2
            ;;
        --embedding-batch-size)
            EMBEDDING_BATCH_SIZE="$2"
            shift 2
            ;;
        --embedding-force-cpu)
            EMBEDDING_BATCH_SIZE=128
            EMBEDDING_FORCE_CPU_ARG=--embedding-force-cpu
            shift
            ;;
        --is-chr-combined)
            IS_CHR_COMBINED_ARG=--is-chr-combined
            shift
            ;;
        --commit)
            COMMIT_ARG=--commit
            shift
            ;;
        --debug)
            DEBUG_ARG=--debug
            shift
            ;;
        --help|-h)
            usage
            exit 0
            ;;
        *)
            echo "Unknown argument: $1" >&2
            usage
            exit 1
            ;;
    esac
done

if [[ -z "$VEP_RESULT_DIR" ]]; then
    usage
    exit 1
fi

process_vep() {
    local vep_result_file="$1"
    local filename=$(basename "$vep_result_file")

    echo "loading $filename"
    runpipe-plugin --plugin VEPAnnotationLoader \
        --file "$vep_result_file" \
        --seqrepo-data-proxy "$DATA_DIR/shared/seqrepo/2024-12-20" \
        --log-path "$VEP_RESULT_DIR/${filename}-load.log" \
        --embedding-batch-size "$EMBEDDING_BATCH_SIZE" \
        --skip-summarization \
        --batch-size "$BATCH_SIZE" \
        $EMBEDDING_FORCE_CPU_ARG $IS_CHR_COMBINED_ARG $COMMIT_ARG $DEBUG_ARG
}

export -f process_vep
export VEP_RESULT_DIR COMMIT_ARG DEBUG_ARG IS_CHR_COMBINED_ARG EMBEDDING_FORCE_CPU_ARG
export DATA_DIR BATCH_SIZE EMBEDDING_BATCH_SIZE

find "$VEP_RESULT_DIR" -maxdepth 1 -name "*.json.gz" -type f -print0 |
    xargs -0 -P "$NUM_PARALLEL" -I {} bash -c 'process_vep "$@"' _ {}
