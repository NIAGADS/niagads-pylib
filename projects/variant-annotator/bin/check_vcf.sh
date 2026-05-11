#!/bin/bash

FASTA_FILE=$DATA_DIR/vep_cache/homo_sapiens/115_GRCh38/Homo_sapiens.GRCh38.dna.toplevel.fa.gz
CHROM_MAP=$PROJECT_DIR/niagads-pylib/projects/variant-annotator/data/bcftools_chrN_to_N_mapping.txt

if [[ -z "$1" ]]; then
  echo "Usage: $0 <file> [e|w]" >&2
  echo "  <file>: VCF file to check" >&2
  echo "  [e|w]: Exit on error (e) or warn (w) (default: e)" >&2
  exit 1
fi

FILE="$1"
MODE="${2:-e}"

bcftools reheader \
    -h $PROJECT_DIR/niagads-pylib/projects/variant-annotator/data/vcf_header.txt "$FILE" \
    | bcftools annotate --rename-chrs "$CHROM_MAP" \
    | bcftools view -e 'FILTER ~ "MONOALLELIC"' | \
    bcftools norm -f "$FASTA_FILE" -c "$MODE" >/dev/null