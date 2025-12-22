"""variant annotator functions"""

from niagads.enums.core import CaseInsensitiveEnum
from niagads.genomics.features.region.core import GenomicRegion
from niagads.genomics.sequence.chromosome import Human
from pydantic import BaseModel, Field, model_validator
from ga4gh.vrs.models import Allele


class VariantType(CaseInsensitiveEnum):
    SNV = "single-nucleotide variant"
    MNV = "multi-nucleotide variant"
    INDEL = "insertion-deletion"
    DEL = "deletion"
    INS = "insertion"
    SV = "structural variant"


class Variant(BaseModel, GenomicRegion):
    length: int = Field(description="variant length")
    ref: str
    alt: str
    ref_snp_id: str = None
    positional_id: str = None
    type: VariantType = None
    verified: bool = False
    primary_key: str = Field(default=None, description="database primary key")
    ga4gh_vrs: Allele = None

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
        if self.type == VariantType.SV and self.length is None:
            raise ValueError(
                "Must assign length of `structural variant` (`SV`) when initializing."
            )

        if self.type in [VariantType.SNV, VariantType.INS]:
            # SNV and INS: length is 1
            self.length = 1
        else:  # MVN, INDEL, DEL length = length of ref
            self.length = len(self.ref)
        return self

    @model_validator(mode="after")
    def resolve_variant_type(self):
        if self.length and self.length >= 50:
            self.type = VariantType.SV

        else:
            len_ref = len(self.ref)
            len_alt = len(self.alt)
            if len_ref >= 50 or len_alt >= 50:
                self.type = VariantType.SV
            elif len_ref == 1 and len_alt == 1:
                self.type = VariantType.SNV
            elif len_ref == len_alt and len_ref > 1:
                self.type = VariantType.MNV
            elif len_ref == 0 and len_alt > 0:
                self.type = VariantType.INS
            elif len_ref > 0 and len_alt == 0:
                self.type = VariantType.DEL
            elif len_ref > 0 and len_alt > 0:
                self.type = VariantType.INDEL

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
