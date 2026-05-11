#!/bin/bash

# Run VEP annotation on all VCF files in a directory in parallel
# Usage: ./run_vep_parallel.sh <directory> [max_parallel_jobs]

# set -e

SCRIPT_DIR=$PROJECT_DIR/niagads-pylib/projects/variant-annotator/bin
VEP_SCRIPT="${SCRIPT_DIR}/vep.sh"

# Parse arguments
if [[ $# -lt 1 ]]; then
  echo "Usage: $0 <vcf_directory> [--max-parallel N] [--fork N] [--buffer-size N] [--stats]" >&2
  echo "  <vcf_directory>: Directory containing VCF files" >&2
  echo "  [--max-parallel N]: Maximum number of parallel jobs (default: 4)" >&2
  echo "  [--fork N]: Number of VEP forks (default: 3)" >&2
  echo "  [--buffer-size N]: VEP buffer size (default: 10000)" >&2
  echo "  [--stats]: Generate statistics (default: no stats)" >&2
  exit 1
fi

VCF_DIR="$1"
MAX_PARALLEL=4
FORK=3
BUFFER_SIZE=10000
NO_STATS=true

shift
while [[ $# -gt 0 ]]; do
  case "$1" in
    --max-parallel)
      MAX_PARALLEL="$2"
      shift 2
      ;;
    --fork)
      FORK="$2"
      shift 2
      ;;
    --buffer-size)
      BUFFER_SIZE="$2"
      shift 2
      ;;
    --stats)
      NO_STATS=false
      shift
      ;;
    *)
      echo "Unknown argument: $1" >&2
      exit 1
      ;;
  esac
done

if [[ ! -d "$VCF_DIR" ]]; then
  echo "Error: Directory '$VCF_DIR' does not exist" >&2
  exit 1
fi

if [[ ! -f "$VEP_SCRIPT" ]]; then
  echo "Error: VEP script not found at '$VEP_SCRIPT'" >&2
  exit 1
fi

# Find all VCF files
VCF_FILES=("$VCF_DIR"/*.vcf "$VCF_DIR"/*.vcf.gz)
VCF_FILES=("${VCF_FILES[@]}" "$VCF_DIR"/*.VCF "$VCF_DIR"/*.VCF.gz)

# Filter to only existing files
VALID_FILES=()
for file in "${VCF_FILES[@]}"; do
  if [[ -f "$file" ]]; then
    VALID_FILES+=("$file")
  fi
done

if [[ ${#VALID_FILES[@]} -eq 0 ]]; then
  echo "Error: No VCF files found in '$VCF_DIR'" >&2
  exit 1
fi

# Sort files by size (largest first)
mapfile -t VALID_FILES < <(printf '%s\n' "${VALID_FILES[@]}" | xargs ls -S)

echo "Found ${#VALID_FILES[@]} VCF file(s) to process"
echo "Processing with max $MAX_PARALLEL parallel jobs"
echo "And allowing with $FORK VEP Forks"
echo ""

# Process files in parallel using GNU Parallel or xargs
run_single_vep() {
  local vcf_file="$1"
  local basename="$(basename "$vcf_file")"
  echo "[$(date +'%Y-%m-%d %H:%M:%S')] Starting VEP for $basename"
  local vep_args="--file $vcf_file --fork $FORK --buffer-size $BUFFER_SIZE"
  [[ "$NO_STATS" == "false" ]] && vep_args="$vep_args --stats" || true
  if "$VEP_SCRIPT" $vep_args; then
    echo "[$(date +'%Y-%m-%d %H:%M:%S')] Completed VEP for $basename"
  else
    echo "[$(date +'%Y-%m-%d %H:%M:%S')] FAILED VEP for $basename" >&2
    return 1
  fi
}

export VEP_SCRIPT
export FORK
export BUFFER_SIZE
export NO_STATS
export -f run_single_vep

# Use GNU Parallel if available, otherwise fall back to xargs
if command -v parallel &> /dev/null; then
  printf '%s\n' "${VALID_FILES[@]}" | parallel -j "$MAX_PARALLEL" run_single_vep
else
  printf '%s\0' "${VALID_FILES[@]}" | xargs -0 -P "$MAX_PARALLEL" -I {} bash -c 'run_single_vep "$@"' _ {}
fi

echo ""
echo "All VCF files processed"
