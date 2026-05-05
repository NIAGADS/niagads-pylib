#!/bin/bash

SV_CADD_CONFIG="sv=/data/cadd/gnomAD_SV_release_v2.1.tsv.gz"
DEFAULT_CADD_CONFIG="snv=/data/cadd/whole_genome_SNVs.tsv.gz,indels=/data/cadd/gnomad.genomes.r4.0.indel.tsv.gz,${SV_CADD_CONFIG}"

IS_SV=0

# Parse named arguments: --file and --is-sv
while [[ $# -gt 0 ]]; do
  key="$1"
  case $key in
    --file)
      FILE="$2"
      shift # past argument
      shift # past value
      ;;
    --is-sv)
      IS_SV=1
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
mkdir -p $WORKING_DIR/vep_output

INPUT_FILE_BASENAME=$(basename "$FILE")
INPUT_FILE=/working/${INPUT_FILE_BASENAME}

OUTPUT_DIR=/working/vep_output
OUTPUT_FILE_PREFIX=${OUTPUT_DIR}/${INPUT_FILE_BASENAME}
OUTPUT_FILE=${OUTPUT_FILE_PREFIX}.vep.json.gz
ERROR_FILE=${OUTPUT_FILE_PREFIX}.vep.errors
LOG_FILE=${OUTPUT_FILE_PREFIX}.vep.log

FASTA_FILE=/data/homo_sapiens/115_GRCh38/Homo_sapiens.GRCh38.dna.toplevel.fa.gz

# Set cadd_config based on IS_SV
if [[ "$IS_SV" -eq 1 ]]; then
   CADD_CONFIG=$SV_CADD_CONFIG
else
   CADD_CONFIG=$DEFAULT_CADD_CONFIG
fi



echo "WORKING_DIR=$WORKING_DIR"
echo "INPUT_FILE_BASE_NAME=$INPUT_FILE_BASENAME"
echo "INPUT_FILE=$INPUT_FILE"
echo "OUTPUT_FILE=$OUTPUT_FILE"
echo "CADD_CONFIG=$CADD_CONFIG"

#   
if 

docker compose --env-file $PROJECT_DIR/niagads-pylib/projects/variant-annotator/.env --file $PROJECT_DIR/niagads-pylib/projects/variant-annotator/docker-compose.yaml \
    run --rm -v ${WORKING_DIR}:/working \
  vep \
  --input_file="${INPUT_FILE}" \
  --output_file="${OUTPUT_FILE}" \
  --skipped_variants_file="${OUTPUT_FILE_PREFIX}.skipped" \
  --no_check_variants_order \
  --format vcf \
  --compress_output gzip \
  --cache \
  --fork 4 \
  --offline \
  --no_stats \
  --json \
  --hgvs \
  --fasta="${FASTA_FILE}" \
  --ccds \
  --symbol \
  --numbers \
  --domains \
  --regulatory \
  --canonical \
  --protein \
  --biotype \
  --tsl \
  --pubmed \
  --uniprot \
  --variant_class \
  --exclude_predicted \
  --gencode_basic \
  --af \
  --af_1kg \
  --af_gnomadg \
  --af_gnomade \
  --clin_sig_allele 1 \
  --nearest gene \
  --gene_phenotype \
  --plugin TSSDistance \
  --plugin Enformer,file=/data/enformer/enformer_grch38.vcf.gz \
  --plugin NMD \
  --plugin LoFtool,/data/LoFtool_scores.txt \
  --plugin CADD,"${CADD_CONFIG}" \
  --force_overwrite \
  --verbose \
  --warning_file="${ERROR_FILE}" \

then
    echo "SUCCESS"
else
    echo "FAIL"
fi
