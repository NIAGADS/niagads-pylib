#!/bin/bash

# Run VEP annotation on all VCF files in a directory in parallel
# Usage: ./run_vep_parallel.sh <directory> [max_parallel_jobs]

set -e

SCRIPT_DIR=$PROJECT_DIR/niagads-pylib/projects/variant-annotator/bin
VEP_SCRIPT="${SCRIPT_DIR}/vep.sh"

# Parse arguments
if [[ $# -lt 1 ]]; then
  echo "Usage: $0 <vcf_directory> [max_parallel_jobs]" >&2
  echo "  <vcf_directory>: Directory containing VCF files" >&2
  echo "  [max_parallel_jobs]: Maximum number of parallel jobs (default: 4)" >&2
  exit 1
fi

VCF_DIR="$1"
MAX_PARALLEL="${2:-4}"
FORK="${3:-3}"

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

echo "Found ${#VALID_FILES[@]} VCF file(s) to process"
echo "Processing with max $MAX_PARALLEL parallel jobs"
echo ""

# Process files in parallel using GNU Parallel or xargs
run_single_vep() {
  local vcf_file="$1"
  local basename="$(basename "$vcf_file")"
  echo "[$(date +'%Y-%m-%d %H:%M:%S')] Starting VEP for $basename"
  if "$VEP_SCRIPT" --file "$vcf_file" --fork "$FORK"; then
    echo "[$(date +'%Y-%m-%d %H:%M:%S')] Completed VEP for $basename"
  else
    echo "[$(date +'%Y-%m-%d %H:%M:%S')] FAILED VEP for $basename" >&2
    return 1
  fi
}

export VEP_SCRIPT
export -f run_single_vep

# Use GNU Parallel if available, otherwise fall back to xargs
if command -v parallel &> /dev/null; then
  printf '%s\n' "${VALID_FILES[@]}" | parallel -j "$MAX_PARALLEL" run_single_vep
else
  printf '%s\0' "${VALID_FILES[@]}" | xargs -0 -P "$MAX_PARALLEL" -I {} bash -c 'run_single_vep "$@"' _ {}
fi

echo ""
echo "All VCF files processed"
