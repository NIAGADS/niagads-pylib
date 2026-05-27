#!/usr/bin/env bash

infile="$1"
outdir="$(dirname "$infile")"

if [[ "$infile" == *.gz ]]; then
  zcat "$infile"
else
  cat "$infile"
fi | awk -F'\t' -v outdir="$outdir" '
BEGIN {OFS="\t"}
/^#/ {header = header $0 ORS; next}
{
  f = outdir "/" $1 ".vcf"
  if (!(f in seen)) {
    printf "%s", header > f
    seen[f]=1
  }
  print > f
}
'