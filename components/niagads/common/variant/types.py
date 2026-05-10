from enum import auto

from niagads.common.variant.models.record import VariantIdentifier
from niagads.enums.core import CaseInsensitiveEnum
from niagads.utils.list import qw


class LDPartner(VariantIdentifier):
    """Represents a variant in linkage disequilibrium (LD) with another variant.

    Inherits from VariantIdentifier:
        ref_snp_id (Optional[str]): Reference SNP ID (e.g., rsID).
        positional_id (str): Positional variant identifier.

    Additional LD attributes:
        r_squared (float): Squared correlation coefficient (r²) between variants.
        r (float): Correlation coefficient between variants.
        d (float): D statistic for LD.
        d_prime (float): D' statistic for LD.
    """

    r_squared: float
    r: float
    d: float
    d_prime: float


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
