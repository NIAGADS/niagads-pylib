from niagads.enums.core import CaseInsensitiveEnum


class NIAGADSResources(CaseInsensitiveEnum):
    NIAGADS = "https://www.niagads.org"
    NIAGADS_DSS = "https://dss.niagads.org"
    ADVP = "https://advp.niagads.org"
    FILER = "https://tf.lisanwanglab.org/FILER"
    FILER_API = "https://tf.lisanwanglab.org/FILER2/"
    FILER_DOWNLOADS = "https://tf.lisanwanglab.org/GADB"
    GENOMICSDB = "https://www.niagads.org/genomics"

    @classmethod
    def _missing_(cls, value: str):
        key = value.upper().replace("-", "_").replace(" ", "_")
        try:
            return cls.__members__[key]
        except ValueError as err:
            raise err


class ThirdPartyResources(CaseInsensitiveEnum):
    PUBMED = "https://pubmed.ncbi.nlm.nih.gov"
    PUBMED_API = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils/esummary.fcgi?db=pubmed&retmode=json&id="
    DASHR2 = "http://dashr2.lisanwanglab.org/index.php"
    ENCODE = "https://www.encodeproject.org"
    EPIMAP = "https://compbio.mit.edu/epimap/"
    FANTOM5 = "http://fantom.gsc.riken.jp/5/"
    FANTOM5_SLIDEBASE = "http://slidebase.binf.ku.dk"
    FACTORBOOK = "https://genome.ucsc.edu/index.html"
    FACTORBOOK_LIFTED = "https://genome.ucsc.edu/index.html"
    INFERNO = "http://inferno.lisanwanglab.org/index.php"
    GTEX = "https://gtexportal.org"
    HOMER = "http://homer.ucsd.edu/homer"
    ROADMAP = "http://www.roadmapepigenomics.org"
    TARGETSCAN_V7P2 = "http://www.targetscan.org/vert_72"
    ENSEMBL = "https://www.ensembl.org"
    CEEHRC = "http://epigenomesportal.ca/ihec"
    IHEC_EPIGENOMES = "https://ihec-epigenomes.org/"
    ONE_K_GENOME_PHASE3 = "https://www.internationalgenome.org/category/phase-3"
    THREE_DGENOME = "https://3dgenome.fsm.northwestern.edu"
    BLUEPRINT = "https://ihec-epigenomes.org/research/projects/blueprint/"
    EPIHK = "https://epihk.org/"
    CADD = "https://cadd.gs.washington.edu/"
    UCSC = "https://genome.ucsc.edu/"
    DBSNP = "https://www.ncbi.nlm.nih.gov/snp/"
    EQTL_CATALOGUE = "https://www.ebi.ac.uk/eqtl/"
    GENCODE = "https://www.gencodegenes.org/"
    GWAS_CATALOG = "https://www.ebi.ac.uk/gwas/"
    REFSEQ = "https://www.ncbi.nlm.nih.gov/refseq/"
    TF_FOOTPRINT_ATLAS = "https://doi.org/10.1016/j.celrep.2020.108029"

    def __replace_leading_digit_with_word(s: str) -> str:
        digit_map = {
            "1": "ONE",
            "2": "TWO",
            "3": "THREE",
            "4": "FOUR",
            "5": "FIVE",
            "6": "SIX",
            "7": "SEVEN",
            "8": "EIGHT",
            "9": "NINE",
        }
        if s and s[0] in digit_map:
            return f"{digit_map[s[0]]}_{s[1:]}"
        return s

    @classmethod
    def _missing_(cls, value: str):
        """handle versions; e.g., DASHR2|small_RNA_Genes" -> DASHR2_SMALL_RNA_GENES"""
        key = cls.__replace_leading_digit_with_word(
            value.upper().replace("|", "_").replace("-", "_").replace(" ", "_")
        )
        try:
            return cls.__members__[key]
        except ValueError as err:
            raise err
