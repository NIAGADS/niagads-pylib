from enum import auto

from niagads.enums.core import CaseInsensitiveEnum
from niagads.utils.list import qw


class VariantClass(CaseInsensitiveEnum):
    SNV = "single-nucleotide variant"
    MNV = "multi-nucleotide variant"
    SHORT_INDEL = "insertion-deletion (short)"
    SHORT_DEL = "deletion (short)"
    SHORT_INS = "insertion (short)"
    INDEL = "insertion-deletion (SV)"
    DEL = "deletion (SV)"
    INS = "insertion (SV)"
    DUP = "duplication"
    INV = "inversion"
    TRANS = "translocation"
    CNV = "copy-number variation"
    MEI = "mobile-element insertion"
    SV = "structural variant"

    def __str__(self):
        return self.name

    def is_short_indel(self):
        return self.name.startswith("SHORT")

    def is_structural_variant(self):
        return self.name in qw("DEL INS INDEL DUP INV TRANS CNV MEI SV")


class ConsequenceImpact(CaseInsensitiveEnum):
    HIGH = auto()
    MODERATE = auto()
    LOW = auto()
    MODIFIER = auto()

    @classmethod
    def color(self):
        match self.name:
            case "HIGH" | "high":
                return "#ff00ff"
            case "MODERATE" | "moderate":
                return "#f59300"
            case "MODIFIER" | "modifier":
                return "#377eb8"
            case "LOW" | "low":
                return "#377eb8"
            case _:
                raise ValueError(f"Invalid consequence impact: {str(self)}")
