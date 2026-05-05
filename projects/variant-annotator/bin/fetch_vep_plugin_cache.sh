#!/bin/bash
source .env

# === create cache; install plugin code
# docker compose run -e MODE=install --rm vep

# LofTool

wget -O $HOST_VEP_CACHE_DIR/LoFtool_scores.txt https://raw.githubusercontent.com/Ensembl/VEP_plugins/refs/heads/release/115/LoFtool_scores.txt

# Enformer
mkdir -p $HOST_VEP_CACHE_DIR/enformer
wget -O $HOST_VEP_CACHE_DIR/enformer/enformer_grch38.vcf.gz https://ftp.ensembl.org/pub/current_variation/Enformer/enformer_grch38.vcf.gz
wget -O $HOST_VEP_CACHE_DIR/enformer/enformer_grch38.vcf.gz.tbi https://ftp.ensembl.org/pub/current_variation/Enformer/enformer_grch38.vcf.gz.tbi


# === install required plugin data
# CADD
mkdir -p $HOST_VEP_CACHE_DIR/cadd
wget -O $HOST_VEP_CACHE_DIR/cadd/whole_genome_SNVs.tsv.gz https://kircherlab.bihealth.org/download/CADD/v1.7/GRCh38/whole_genome_SNVs.tsv.gz
wget -O $HOST_VEP_CACHE_DIR/cadd/whole_genome_SNVs.tsv.gz.tbi https://kircherlab.bihealth.org/download/CADD/v1.7/GRCh38/whole_genome_SNVs.tsv.gz.tbi

wget -O $HOST_VEP_CACHE_DIR/cadd/gnomad.genomes.r4.0.indel.tsv.gz https://kircherlab.bihealth.org/download/CADD/v1.7/GRCh38/gnomad.genomes.r4.0.indel.tsv.gz
wget -O $HOST_VEP_CACHE_DIR/cadd/gnomad.genomes.r4.0.indel.tsv.gz.tbi https://kircherlab.bihealth.org/download/CADD/v1.7/GRCh38/gnomad.genomes.r4.0.indel.tsv.gz.tbi

wget -O $HOST_VEP_CACHE_DIR/cadd/gnomAD_SV_release_v2.1.tsv.gz https://kircherlab.bihealth.org/download/CADD-SV/v1.1/gnomAD_SV_release_v2.1.tsv.gz
wget -O $HOST_VEP_CACHE_DIR/cadd/gnomAD_SV_release_v2.1.tsv.gz.tbi https://kircherlab.bihealth.org/download/CADD-SV/v1.1/gnomAD_SV_release_v2.1.tsv.gz.tbi

# dbNSFP - TODO later

