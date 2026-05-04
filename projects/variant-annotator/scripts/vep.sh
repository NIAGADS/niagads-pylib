#!/bin/bash

# SV_CADD_CONFIG="sv=/data/cadd/gnomAD_SV_release_v2.1.tsv.gz"
# DEFAULT_CADD_CONFIG="snv=/data/cadd/whole_genome_SNVs.tsv.gz,indels=/data/cadd/gnomad.genomes.r4.0.indel.tsv.gz"

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
INPUT_FILE_BASENAME=$(basename "$FILE")
INPUT_FILE=/working/${INPUT_FILE_BASE_NAME}
OUTPUT_FILE=${INPUT_FILE}.vep.json.gz
ERROR_FILE=${INPUT_FILE}.vep.errors
LOG_FILE=${INPUT_FILE}.vep.log


# Set cadd_config based on IS_SV
if [[ "$IS_SV" -eq 1 ]]; then
  CADD_CONFIG=DEFAULT_CADD_CONFIG
else
  CADD_CONFIG=SV_CADD_CONFIG
fi

if 

docker compose run --rm -v ${WORKING_DIR}:/working:z \
  --f $PROJECT_HOME/niagads-pylib/projects/variant-annotator/docker-compose.yaml \
  vep  \
  --input_file $INPUT_FILE \
  --output_file $OUTPUT_FILE \
  --skipped_variants_file $OUTPUT_FILE.skipped \
  --no_check_variants_order \
  --format vcf \
  --compress_output gzip \
  --cache \
  --dir_cache /data \
  --offline \
  --no_stats \
  --json \
  --fork 8 \
  --hgvs \
  --fasta /data \
  --sift b \
  --polyphen b \
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
  --pubmed \
  --clin_sig_allele 1 \
  --nearest gene \
  --gene_phenotype \
  --plugin TSSDistance \
  --plugin Enformer,file=/data/enformer/enformer_grch38.vcf.gz \
  --plugin NMD \
  --plugin LoFtool,/data/LoFtool_scores.txt \
  --force_overwrite \
  --verbose \
  --warning_file  $ERROR_FILE 

  # --plugin CADD,$CADD_CONFIG \

then
    echo "SUCCESS"
else
    echo "FAIL"
fi
