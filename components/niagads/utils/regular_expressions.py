from enum import StrEnum


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
    VARIANT = r"^.+:\d+:[ACGT]+:[ACGT]+$"
    REFSNP = r"^rs\d+$"
    STRUCTUAL_VARIANT = (
        r"^(DEL|INS|DUP|INV|CNV|TRA)_CHR(\d{1,2}|[XYM]|MT)_([A-Z]|\d){8}$"
    )
    GENOMIC_LOCATION = r"^(chr)?(1[0-9]|2[0-2]|[1-9]|X|Y|M)[:\-](\d+)[\-:](\d+)$"
    # Mantissa: 1-3 digits, optional . and up to 2 decimals; Exponent: e- and 1-3 digits
    PVALUE_SCIENTIFIC_NOTATION = (
        r"^[1-9]\d{0,2}(\.\d{1,2})?e-\d{1,3}$" r"^[1-9]\d*(\.\d+)?e-\d+$"
    )
