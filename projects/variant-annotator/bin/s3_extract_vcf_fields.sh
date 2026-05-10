#!/bin/bash

# Downloads VCF files from S3 and extracts fields 1-9 to .vcf files (ignoring sample data)
# Usage: extract_vcf_fields.sh <s3_path> <extension> [parallel_jobs]

set -euo pipefail

s3_path="${1%/}"
ext="$2"
parallel_jobs="${3:-10}"
logfile="extract_vcf_fields.log"

# Extract bucket name from s3_path
s3_bucket=$(echo "$s3_path" | sed 's|s3://\([^/]*\).*|\1|')

process_file() {
    local s3_bucket="$1"
    local file="$2"
    local ext="$3"
    local logfile="$4"
    local name=$(basename "$file" | sed "s/\.$ext$//")
    name="${name//:/_}"
    local tmp=$(mktemp -p .)
    aws s3 cp --no-progress "s3://$s3_bucket/$file" - | pigz -dc | cut -f1-9 > "$name"
    echo "$name" >> "$logfile"
}

export -f process_file

files=$(aws s3 ls "$s3_path/" --recursive | awk '{print $4}' | grep "\.$ext$")
echo "$files" | xargs -P "$parallel_jobs" -I {} bash -c "process_file $s3_bucket {} $ext $logfile"
