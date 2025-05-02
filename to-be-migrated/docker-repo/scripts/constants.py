from types import SimpleNamespace

SCHEMA = "ServerApplication"
FILER_TABLE = "FILERTrack"

SHARD_PATTERN = r"_chr(\d{1,2}|[XYM]|MT)_"

DATASET_TYPES = ["GWAS_sumstats", "QTL_sumstats"]
GENOME_BUILDS = ["GRCh37", "GRCh38", "grch38", "grch37", "hg38", "hg19"]
ALLOWABLE_FILER_TRACK_FILTERS = {
    "dataSource": "original data source ",
    "assay": "assay type",
    "featureType": "feature type",
    "antibodyTarget": "target of ChIP-seq or other immunoprecipitation assay",
    "project": "member of a collection of related tracks, often an ENCODE project",
    "tissue": "tissue associated with biosample",
}

ADSP_VARIANTS_ACCESSION = "NG00067"
