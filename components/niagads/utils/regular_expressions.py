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
