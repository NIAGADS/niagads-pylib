#!/bin/bash
 
#   set -x

set -o pipefail

FORK=2
BUFFER_SIZE=10000
NO_STATS=true


# Parse named arguments: --file and --is-sv
while [[ $# -gt 0 ]]; do
  key="$1"
  case $key in
    --file)
      FILE="$2"
      shift # past argument
      shift # past value
      ;;
    --fork)
      FORK="$2"
      shift # past argument
      shift # past value
      ;;
    --buffer-size)
      BUFFER_SIZE="$2"
      shift # past argument
      shift # past value
      ;;
    --stats)
      NO_STATS=false
      shift # past argument
      ;;
    *)
      echo "Unknown argument: $1" >&2
      exit 1
      ;;
  esac
done

if [[ -z "$FILE" ]]; then
  echo "--file argument is required" >&2
  exit 1
fi

WORKING_DIR=$(dirname "$FILE")
FILE_NAME=$(basename "$FILE")

INPUT_FILE=/working/${FILE_NAME}
OUTPUT_FILE=${INPUT_FILE}.vep.json.gz
ERROR_FILE=${INPUT_FILE}.vep.errors
SKIP_FILE=${INPUT_FILE}.vep.skipped
LOG_FILE=${FILE}.vep.log


if bcftools reheader -h $PROJECT_DIR/niagads-pylib/projects/variant-annotator/data/vcf_header.txt $FILE | bcftools view -e 'FILTER ~ "MONOALLELIC"' | \
docker compose --env-file $PROJECT_DIR/niagads-pylib/projects/variant-annotator/.env --file $PROJECT_DIR/niagads-pylib/projects/variant-annotator/docker-compose.yaml \
    run --rm -T -v ${WORKING_DIR}:/working vep \
  vep \
  --input_file stdin \
  --output_file="${OUTPUT_FILE}" \
  --skipped_variants_file="${SKIP_FILE}" \
  --warning_file="${ERROR_FILE}" \
  --no_check_variants_order \
  $([[ "$NO_STATS" == "true" ]] && echo "--no_stats") \
  --format vcf \
  --force_overwrite \
  --compress_output gzip \
  --cache \
  --verbose \
  --fork="${FORK}" \
  --json \
  --offline \
  --everything \
  --buffer_size="${BUFFER_SIZE}" \
  --plugin TSSDistance \
  --plugin Enformer,file=/data/enformer/enformer_grch38.vcf.gz \
  --plugin NMD \
  --plugin LoFtool,/data/LoFtool_scores.txt \
  --plugin CADD,snv=/data/cadd/whole_genome_SNVs.tsv.gz,indels=/data/cadd/gnomad.genomes.r4.0.indel.tsv.gz \
  2>&1 | tee "${LOG_FILE}" > /dev/null
then
    echo "SUCCESS VEP - $FILE" | tee -a "${LOG_FILE}" > /dev/null
else
    echo "FAIL VEP - $FILE" | tee -a "${LOG_FILE}" > /dev/null
fi
