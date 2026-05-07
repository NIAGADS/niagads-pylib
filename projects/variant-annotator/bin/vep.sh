#!/bin/bash
 
#   set -x

FORK=2

# Parse named arguments: --file and --is-sv
while [[ $# -gt 0 ]]; do
  key="$1"
  case $key in
    --file)
      FILE="$2"
      shift # past argument
      shift # past value
      ;;
    *)
    --fork)
      FORK="$2"
      shift # past argument
      shift # past value
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


echo "WORKING_DIR=$WORKING_DIR"
echo "INPUT_FILE=$INPUT_FILE"
echo "OUTPUT_FILE=$OUTPUT_FILE"


if 

docker compose --env-file $PROJECT_DIR/niagads-pylib/projects/variant-annotator/.env --file $PROJECT_DIR/niagads-pylib/projects/variant-annotator/docker-compose.yaml \
    run --rm -T -v ${WORKING_DIR}:/working vep \
  vep \
  --input_file="${INPUT_FILE}" \
  --output_file="${OUTPUT_FILE}" \
  --skipped_variants_file="${SKIP_FILE}" \
  --warning_file="${ERROR_FILE}" \
  --no_check_variants_order \
  --format vcf \
  --compress_output gzip \
  --force_overwrite \
  --cache \
  --verbose \
  --fork="${FORK}" \
  --no_stats \
  --json \
  --offline \
  --everything \
  --plugin TSSDistance \
  --plugin Enformer,file=/data/enformer/enformer_grch38.vcf.gz \
  --plugin NMD \
  --plugin LoFtool,/data/LoFtool_scores.txt \
  --plugin CADD,snv=/data/cadd/whole_genome_SNVs.tsv.gz,indels=/data/cadd/gnomad.genomes.r4.0.indel.tsv.gz >  /dev/null 2> "${LOG_FILE}"


then
    echo "SUCCESS"
else
    echo "FAIL"
fi
