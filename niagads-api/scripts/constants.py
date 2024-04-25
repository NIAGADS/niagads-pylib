from types import SimpleNamespace


DATASET_TYPES = ["GWAS_sumstats", "QTL_sumstats"]
GENOME_BUILDS = ["GRCh37", "GRCh38", "grch38", "grch37", "hg38", "hg19"]
ALLOWABLE_FILER_TRACK_FILTERS = {
    "dataSource": "original data source ", 
    "assay": "assay type", 
    "featureType": "feature type", 
    "antibodyTarget": "target of ChIP-seq or other immunoprecipitation assay",
    "project": "member of a collection of related tracks, often an ENCODE project",
    "tissue": "tissue associated with biosample"
    }

ADSP_VARIANTS_ACCESSION = "NG00067"

__urls = ({
        'pubmed': 'https://pubmed.ncbi.nlm.nih.gov', 
        'niagads': 'https://www.niagads.org', 
        'advp': 'https://advp.niagads.org',
        'filer_api': 'https://tf.lisanwanglab.org/FILER',
        'filer': 'https://tf.lisanwanglab.org/FILER',
        'filer_downloads': 'https://tf.lisanwanglab.org/GADB',
        'pubmed_api':'https://eutils.ncbi.nlm.nih.gov/entrez/eutils/esummary.fcgi?db=pubmed&retmode=json&id='
})

__datasource_urls = ({
        'DASHR2': 'http://dashr2.lisanwanglab.org/index.php',
        'DASHR2|small_RNA_Genes': 'http://dashr2.lisanwanglab.org/index.php',
        'ENCODE': 'https://www.encodeproject.org',
        'EpiMap': 'https://personal.broadinstitute.org/cboix/epimap/ChromHMM/',
        'FANTOM5': 'http://fantom.gsc.riken.jp/5/',
        'FANTOM5|Enhancers_SlideBase': 'http://slidebase.binf.ku.dk/',
        'FANTOM5|Enhancers': 'https://fantom.gsc.riken.jp/5/',
        'FactorBook': 'https://genome.ucsc.edu/index.html',
        'FactorBook|lifted': 'https://genome.ucsc.edu/index.html',
        'INFERNO_genomic_partition': 'http://inferno.lisanwanglab.org/index.php',
        'GTEx|v7': 'https://gtexportal.org/home/',
        'GTEx|v8': 'https://gtexportal.org/home/',
        'HOMER' : 'http://homer.ucsd.edu/homer/',
        'ROADMAP': 'http://www.roadmapepigenomics.org/',
        'ROADMAP|Enhancers' : 'http://www.roadmapepigenomics.org/',
        'ROADMAP|lifted': 'http://www.roadmapepigenomics.org/',
        'Repeats' : 'http://genome.ucsc.edu/cgi-bin/hgTables',
        'TargetScan|v7p2': 'http://www.targetscan.org/vert_72/',
        'TargetScan|v7p2-lifted': 'http://www.targetscan.org/vert_72/' 
})


URLS = SimpleNamespace(**__urls)
DATASOURCE_URLS = SimpleNamespace(**__datasource_urls)