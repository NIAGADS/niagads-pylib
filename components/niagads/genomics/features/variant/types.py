from niagads.enums.core import CaseInsensitiveEnum
from niagads.utils.list import qw


class VariantClass(CaseInsensitiveEnum):
    SNV = "single-nucleotide variant"
    MNV = "multi-nucleotide variant"
    SHORT_INDEL = "insertion-deletion (short)"
    SHORT_DEL = "deletion (short)"
    SHORT_INS = "insertion (short)"
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
