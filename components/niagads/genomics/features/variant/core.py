"""variant annotator functions"""

from niagads.enums.core import CaseInsensitiveEnum
from niagads.genomics.features.region.core import GenomicRegion
from niagads.genomics.sequence.chromosome import Human
from niagads.utils.list import qw
from pydantic import BaseModel, Field, model_validator
from ga4gh.vrs.models import Allele


class VariantClass(CaseInsensitiveEnum):
    SNV = "single-nucleotide variant"
    MNV = "multi-nucleotide variant"
    SHORT_INDEL = "insertion-deletion (short)"
    SHORT_DEL = "deletion (short)"
    SHORT_INS = "insertion (short)"
    DEL = "deletion (SV)"
    INS = "insertion (SV)"
    INDEL = "insertion-deltion (SV)"
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


class Variant(GenomicRegion):
    length: int = Field(description="variant length")
    ref: str
    alt: str
    ref_snp_id: str = None
    positional_id: str = None
    variant_class: VariantClass = None
    verified: bool = False
    primary_key: str = Field(default=None, description="database primary key")
    ga4gh_vrs: Allele = None

    def __str__(self):
        if self.primary_key is not None:
            return self.primary_key
        else:
            if self.variant_class.is_structural_variant():
                return (
                    f"{self.chromosome}:{self.start}/{self.variant_class}:{self.length}"
                )
            else:
                return self.positional_id

    # GenomicRegion parent override
    zero_based: bool = Field(
        default=False, description="flag indicating if region is zero-based"
    )

    @model_validator(mode="after")
    def resolve_length(self):
        return self._resolve_length()

    def _resolve_length(self):
        """
        Determine variant length based on type and length of reference allele
        helper function created b/c needs to be done at initialization and then recalculated
        after normalization
        """
        if self.variant_class == VariantClass.SV and self.length is None:
            raise ValueError(
                "Must assign length of `structural variant` (`SV`) when initializing."
            )

        if self.variant_class in [VariantClass.SNV, VariantClass.SHORT_INS]:
            # SNV and INS: length is 1
            self.length = 1
        else:  # MVN, INDEL, DEL length = length of ref
            self.length = len(self.ref)
        return self

    @model_validator(mode="after")
    def resolve_variant_type(self):
        if self.length and self.length >= 50:
            self.variant_class = VariantClass.SV

        else:
            len_ref = len(self.ref)
            len_alt = len(self.alt)
            if len_ref >= 50 or len_alt >= 50:
                self.variant_class = VariantClass.SV
            elif len_ref == 1 and len_alt == 1:
                self.variant_class = VariantClass.SNV
            elif len_ref == len_alt and len_ref > 1:
                self.variant_class = VariantClass.MNV
            elif len_ref == 0 and len_alt > 0:
                self.variant_class = VariantClass.SHORT_INS
            elif len_ref > 0 and len_alt == 0:
                self.variant_class = VariantClass.SHORT_DEL
            elif len_ref > 0 and len_alt > 0:
                self.variant_class = VariantClass.SHORT_INDEL

        return self

    @classmethod
    def from_positional_id(cls, positional_id: str):
        chrm, start, ref, alt = positional_id.replace("-", ":").split(":")
        return cls(
            chromosome=Human(chrm),
            start=start,
            ref=ref,
            alt=alt,
            positional_id=positional_id,
        )
