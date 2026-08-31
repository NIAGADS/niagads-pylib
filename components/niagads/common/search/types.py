from niagads.enums.core import CaseInsensitiveEnum


class MatchType(CaseInsensitiveEnum):
    EXACT_ID = "exact match to term or identifier"
    EXACT_SYNONYM = (
        "exact match to a synonymous term or obsolete/aliased/deprecated identifier"
    )
    PARTIAL_ID = "partial (exact substring) match to a term, identiifer, or synonym"
    PARTIAL_DESCRIPTIVE = (
        "partial (exact substring) match to a defintion or descriptive annotation field"
    )
    FUZZY = "approximate lexical match to a term or identifier, may match substrings"
    SEMANTIC = "semantic similarity match to term or related text"
    FUZZY_SYNONYM = "approximate lexical match to a synonymous term"
    FUZZY_DESCRIPTIVE = (
        "approximate lexical match to a definition or descriptive annotation field"
    )

    def rank(self) -> int:
        """Return a ranking based on definition order (lower value = more specific match).

        Returns:
            int: Ranking where EXACT=1, SYNONYM=2, ..., SEMANTIC=6.
        """
        members = list(type(self))
        return members.index(self) + 1
