#!/bin/bash

DIR="${1:-}"
JOBS="${2:-4}"

if [[ -z "$DIR" ]]; then
  echo "Usage: $0 <vcf_directory> [jobs]"
  exit 1
fi

find "$DIR" -maxdepth 1 -type f -name "*.vcf" -print0 |
xargs -0 -n 1 -P "$JOBS" bash -c '
f="$1"
dir=$(dirname "$f")

chrom=$(awk "!/^#/ {print \$1; exit}" "$f")

case "$chrom" in
  NC_000001.11) chr="chr1" ;;
  NC_000002.12) chr="chr2" ;;
  NC_000003.12) chr="chr3" ;;
  NC_000004.12) chr="chr4" ;;
  NC_000005.10) chr="chr5" ;;
  NC_000006.12) chr="chr6" ;;
  NC_000007.14) chr="chr7" ;;
  NC_000008.11) chr="chr8" ;;
  NC_000009.12) chr="chr9" ;;
  NC_000010.11) chr="chr10" ;;
  NC_000011.10) chr="chr11" ;;
  NC_000012.12) chr="chr12" ;;
  NC_000013.11) chr="chr13" ;;
  NC_000014.9) chr="chr14" ;;
  NC_000015.10) chr="chr15" ;;
  NC_000016.10) chr="chr16" ;;
  NC_000017.11) chr="chr17" ;;
  NC_000018.10) chr="chr18" ;;
  NC_000019.10) chr="chr19" ;;
  NC_000020.11) chr="chr20" ;;
  NC_000021.9) chr="chr21" ;;
  NC_000022.11) chr="chr22" ;;
  NC_000023.11) chr="chrX" ;;
  NC_000024.10) chr="chrY" ;;
  NC_012920.1) chr="chrMT" ;;
  *) echo "Unknown chromosome in $f: $chrom" >&2; exit 1 ;;
esac

out="${dir}/${chr}.vcf"

awk '"'"'BEGIN{
FS=OFS="\t"
map["NC_000001.11"]="1"; map["NC_000002.12"]="2"; map["NC_000003.12"]="3"
map["NC_000004.12"]="4"; map["NC_000005.10"]="5"; map["NC_000006.12"]="6"
map["NC_000007.14"]="7"; map["NC_000008.11"]="8"; map["NC_000009.12"]="9"
map["NC_000010.11"]="10"; map["NC_000011.10"]="11"; map["NC_000012.12"]="12"
map["NC_000013.11"]="13"; map["NC_000014.9"]="14"; map["NC_000015.10"]="15"
map["NC_000016.10"]="16"; map["NC_000017.11"]="17"; map["NC_000018.10"]="18"
map["NC_000019.10"]="19"; map["NC_000020.11"]="20"; map["NC_000021.9"]="21"
map["NC_000022.11"]="22"; map["NC_000023.11"]="X"; map["NC_000024.10"]="Y"
map["NC_012920.1"]="MT"
}
/^#/ {print; next}
{$1=(map[$1] ? map[$1] : $1); print}'"'"' "$f" > "$out"

echo "Created: $out"
' _