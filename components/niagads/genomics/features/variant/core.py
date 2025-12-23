"""variant annotator functions"""

from niagads.common.models.core import TransformableModel
from niagads.enums.core import CaseInsensitiveEnum
from niagads.genomics.features.region.core import GenomicRegion
from niagads.genomics.sequence.assembly import HumanGenome
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


class Variant(TransformableModel):
    location: GenomicRegion
    ref: str
    alt: str
    ref_snp_id: str = None
    positional_id: str = None
    variant_class: VariantClass = None
    primary_key: str = Field(default=None, description="database primary key")
    ga4gh_vrs: Allele = None

    def __str__(self):
        if self.primary_key is not None:
            return self.primary_key
        else:
            if self.variant_class.is_structural_variant():
                return (
                    f"{self.location.chromosome.value}:{self.location.start}/"
                    f"{self.variant_class}:{self.location.length}"
                )
            else:
                return self.positional_id

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
            self.location.length = 1
        else:  # MVN, INDEL, DEL length = length of ref
            self.location.length = len(self.ref)
        return self

    @model_validator(mode="after")
    def resolve_variant_type(self):

        len_ref = len(self.ref)
        len_alt = len(self.alt)
        if len_ref >= 50 or len_alt >= 50:
            # SV variant classes should have been set
            # at creation
            if self.variant_class is None:
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
        chrm, position, ref, alt = positional_id.replace("-", ":").split(":")
        start = position - 1
        location = GenomicRegion(
            chromosome=HumanGenome(chrm), start=start, length=start + len(ref)
        )
        return cls(
            location=location,
            ref=ref,
            alt=alt,
            positional_id=positional_id,
        )
