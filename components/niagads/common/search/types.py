from niagads.enums.core import CaseInsensitiveEnum


class MatchType(CaseInsensitiveEnum):
    EXACT = "exact match to term or identifier"
    SYNONYM = (
        "exact match to a synonymous term or obsolete/aliased/deprecated identifier"
    )
    SUBSTRING = "substring match to a term or other text"
    FUZZY = "approximate lexical match to a term or related text, may match substrings"
    SEMANTIC = "semantic similarity match to term or related text"
    FUZZY_SYNONYM = "approximate lexical match to a synonymous term"

    def rank(self) -> int:
        """Return a ranking based on definition order (lower value = more specific match).

        Returns:
            int: Ranking where EXACT=1, SYNONYM=2, ..., SEMANTIC=6.
        """
        members = list(type(self))
        return members.index(self) + 1
