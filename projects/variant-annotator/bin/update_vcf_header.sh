#!/bin/bash

# Replace the header in every VCF file in a directory.
# Usage: update_vcf_header.sh <directory>

if [[ -z "$1" ]]; then
    echo "Usage: $0 <directory>" >&2
    exit 1
fi

dir="$1"
header="$PROJECT_DIR/niagads-pylib/projects/variant-annotator/data/short_vcf_header.txt"

for file in "$dir"/*.vcf; do
    [[ ! -f "$file" ]] && continue
    tmp="${file}.tmp"
    cat "$header" > "$tmp"
    sed '/^#/d' "$file" >> "$tmp"
    mv "$tmp" "$file"
    echo "✓ $file"
done
