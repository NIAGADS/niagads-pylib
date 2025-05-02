from enum import StrEnum
from niagads.enums.core import CaseInsensitiveEnum


class NIAGADSResources(CaseInsensitiveEnum):
    NIAGADS = "https://www.niagads.org"
    ADVP = "https://advp.niagads.org"
    FILER = "https://tf.lisanwanglab.org/FILER"
    FILER_DOWNLOADS = 
    GENOMICS = "https://www.niagads.org/genomics"


class ThirdPartyResources(StrEnum):
    PUBMED = "https://pubmed.ncbi.nlm.nih.gov"
    PUBMED_API = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils/esummary.fcgi?db=pubmed&retmode=json&id="
    DASHR2 = "http://dashr2.lisanwanglab.org/index.php"
    DASHR2_SMALL_RNA_GENES = "http://dashr2.lisanwanglab.org/index.php"
    ENCODE = "https://www.encodeproject.org"
    EPIMAP = "https://personal.broadinstitute.org/cboix/epimap/ChromHMM/"
    FANTOM5 = "http://fantom.gsc.riken.jp/5/"
    FANTOM5_ENHANCERS_SLIDEBASE = "http://slidebase.binf.ku.dk/"
    FANTOM5_ENHANCERS = "https://fantom.gsc.riken.jp/5/"
    FACTORBOOK = "https://genome.ucsc.edu/index.html"
    FACTORBOOK_LIFTED = "https://genome.ucsc.edu/index.html"
    INFERNO_GENOMIC_PARTITION = "http://inferno.lisanwanglab.org/index.php"
    GTEX_V7 = "https://gtexportal.org/home/"
    GTEX_V8 = "https://gtexportal.org/home/"
    HOMER = "http://homer.ucsd.edu/homer/"
    ROADMAP = "http://www.roadmapepigenomics.org/"
    ROADMAP_ENHANCERS = "http://www.roadmapepigenomics.org/"
    ROADMAP_LIFTED = "http://www.roadmapepigenomics.org/"
    REPEATS = "http://genome.ucsc.edu/cgi-bin/hgTables"
    TARGETSCAN_V7P2 = "http://www.targetscan.org/vert_72/"
    TARGETSCAN_V7P2_LIFTED = "http://www.targetscan.org/vert_72/"
    ENSEMBL_GENE_MODEL = "https://useast.ensembl.org/info/genome/genebuild/index.html"

    @classmethod
    def __missing__(cls, value: str):
        """handle versions; e.g., DASHR2|small_RNA_Genes" -> DASHR2_SMALL_RNA_GENES"""
        return cls(value.replace("|", "_").replace("-", "_").upper())
