#!/bin/bash

# Extracts fields 1-9 from compressed VCF files in a directory to .vcf files
# Usage: extract_vcf_fields.sh <directory> <extension>

set -euo pipefail

dir="$1"
ext="$2"

for file in "$dir"/*."$ext"; do
    [[ ! -f "$file" ]] && continue
    name=$(basename "$file" | sed "s/\.$ext$//")
    zcat "$file" | cut -f1-9 > "$name.vcf"
    echo "✓ $name.vcf"
done
