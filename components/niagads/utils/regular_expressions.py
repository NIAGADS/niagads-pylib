from sys import version_info

if version_info >= (3.11,):
    from enum import StrEnum
else:
    from strenum import StrEnum

CHROM_PATTERN = r"(?:[1-9]|1[0-9]|2[0-2]|X|Y|M|MT)"


class RegularExpressions(StrEnum):
    """
    commonly used regexps
    """

    PUBMED_ID = r"^([0-9]{8}|PMID:[0-9]{8})$"

    MD5SUM = r"^[a-fA-F0-9]{32}$"

    DOI = r'(10[.][0-9]{4,}(?:[.][0-9]+)*\/(?:(?!["&\'<>])\S)+)$'

    FILE_SIZE = r"^[.0-9]+\s?(K|M|G)$"

    KEY_VALUE_PAIR = r"^[^\s=]+=[^=;]+$"  # key=value

    SHARD = r"chr(\d{1,2}|[XYM]|MT)"

    GENE = r"^(?:[A-Za-z][A-Za-z0-9_.-]*(@)?|\d{5})$"  # matches symbols, ensembl ids, and entrez ids

    CHROMSOME = r"(?:[1-9]|1[0-9]|2[0-2]|X|Y|M|MT)"

    # variant identifiers / nomenclatures
    POSITIONAL_VARIANT_ID = r"^.+:\d+:[ACGT]+:[ACGT]+$"
    REFSNP = r"^rs\d+$"
    STRUCTUAL_VARIANT = (
        r"^(DEL|INS|DUP|INV|CNV|TRA)_CHR(\d{1,2}|[XYM]|MT)_([A-Z]|\d){8}$"
    )
    SPDI = r"^[^:]+:\d+:[ACGTNacgtn-]+:[ACGTNacgtn-]+$"
    GNOMAD_VARIANT_ID = rf"^{CHROM_PATTERN}-\d+-[ACGTN]+-[ACGTN]+$"
    HGVS = r"^[\w\d]+(:g\.)?\d+[ACGTNacgtn>_delinsdupinsinv]+$"
    BEACON_VARIANT_ID = (
        rf"^\s*{CHROM_PATTERN}\s*:\s*\d+\s*[ACGTNacgtn]+\s*>\s*[ACGTNacgtn]+\s*$"
    )

    GENOMIC_LOCATION = rf"^(chr)?{CHROM_PATTERN}[:\-](\d+)[\-:](\d+)$"

    # Mantissa: 1-3 digits, optional . and up to 2 decimals; Exponent: e- and 1-3 digits
    PVALUE_SCIENTIFIC_NOTATION = (
        r"^[1-9]\d{0,2}(\.\d{1,2})?e-\d{1,3}$" r"^[1-9]\d*(\.\d+)?e-\d+$"
    )

    ENSEMBL_GENE_ID = r"^ENSG\d{11}$"  # Ensembl human gene ID (e.g., ENSG00000139618)
    ENSEMBL_TRANSCRIPT_ID = (
        r"^ENST\d{11}$"  # Ensembl human transcript ID (e.g., ENST00000380152)
    )
    ENSEMBL_EXON_ID = r"^ENSE\d{11}$"  # Ensembl human exon ID (e.g., ENSE00003606199)

    CYTOGENIC_LOCATION = (
        r"^(chr)?(\d{1,2}|X|Y|M|MT)(p|q)(\d{1,2}(\.\d+)?)(-(p|q)?\d{1,2}(\.\d+)?)?$"
    )

    # postgresql://<user>:<password>@<host>:<port>/<database>
    POSTGRES_URI = r"^postgresql:\/\/[^:]+:[^@]+@[^:]+:\d+\/[^\/\s]+$"

    URL = r"^https?://[\w.-]+(?:\.[\w\.-]+)+(?:/[\w\-./?%&=]*)?$"
    EXTERNAL_DATABASE_REF = r"^(.+?)\|([^\s|]+)$"  # name|version

    # e.g. GO:1234567 or chebi:15377; but will match with _ as the separator as well
    ONTOLOGY_TERM_ID = r"^[A-Za-z][A-Za-z0-9_]+[:_][A-Za-z0-9_]+$"
