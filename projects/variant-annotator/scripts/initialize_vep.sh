#!/bin/bash
source .env

# === create cache; install plugin code
# docker compose run -e MODE=install --rm vep

# === install required plugin data
# CADD
mkdir -p $VEP_CACHE_PATH/cadd
wget -O $VEP_CACHE_PATH/cadd/whole_genome_SNVs.tsv.gz https://kircherlab.bihealth.org/download/CADD/v1.7/GRCh38/whole_genome_SNVs.tsv.gz
wget -O $VEP_CACHE_PATH/cadd/whole_genome_SNVs.tsv.gz.tbi https://kircherlab.bihealth.org/download/CADD/v1.7/GRCh38/whole_genome_SNVs.tsv.gz.tbi

wget -O $VEP_CACHE_PATH/cadd/gnomad.genomes.r4.0.indel.tsv.gz https://kircherlab.bihealth.org/download/CADD/v1.7/GRCh38/gnomad.genomes.r4.0.indel.tsv.gz
wget -O $VEP_CACHE_PATH/cadd/gnomad.genomes.r4.0.indel.tsv.gz.tbi https://kircherlab.bihealth.org/download/CADD/v1.7/GRCh38/gnomad.genomes.r4.0.indel.tsv.gz.tbi

wget -O $VEP_CACHE_PATH/cadd/gnomAD_SV_release_v2.1.tsv.gz https://kircherlab.bihealth.org/download/CADD-SV/v1.1/gnomAD_SV_release_v2.1.tsv.gz
wget -O $VEP_CACHE_PATH/cadd/gnomAD_SV_release_v2.1.tsv.gz.tbi https://kircherlab.bihealth.org/download/CADD-SV/v1.1/gnomAD_SV_release_v2.1.tsv.gz.tbi

# dbNSFP - TODO later

# LofTool

wget -O $VEP_CACHE_PATH/LoFtool_scores.txt https://raw.githubusercontent.com/Ensembl/VEP_plugins/refs/heads/release/115/LoFtool_scores.txt

# Enformer
mkdir -p $VEP_CACHE_PATH/enformer
wget -O $VEP_CACHE_PATH/enformer/enformer_grch38.vcf.gz https://ftp.ensembl.org/pub/current_variation/Enformer/enformer_grch38.vcf.gz
wget -O $VEP_CACHE_PATH/enformer/enformer_grch38.vcf.gz.tbi https://ftp.ensembl.org/pub/current_variation/Enformer/enformer_grch38.vcf.gz.tbi
