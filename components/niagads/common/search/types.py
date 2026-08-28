from niagads.enums.core import CaseInsensitiveEnum


class MatchType(CaseInsensitiveEnum):
    EXACT = "exact match to term or identifier"
    SYNONYM = (
        "exact match to a synonymous term or obsolete/aliased/deprecated identifier"
    )
    PARTIAL = "partial match to a term or other text"
    FUZZY = "approximate lexical match"
    SEMANTIC = "semantic similarity match"
