"""variant annotator functions"""

from typing import Optional
from ga4gh.vrs.models import Allele
from niagads.common.models.core import TransformableModel
from niagads.genomics.features.region.core import GenomicRegion
from niagads.genomics.features.variant.types import VariantClass
from niagads.genomics.sequence.assembly import HumanGenome
from pydantic import Field, model_validator


class Variant(TransformableModel):
    location: GenomicRegion
    ref: str
    alt: str
    variant_class: VariantClass

    ref_snp_id: Optional[str] = None
    positional_id: Optional[str] = None
    normalized_positional_id: Optional[str] = None
    niagads_unique_id: Optional[str] = Field(
        default=None, description="unique variant identifier in NIAGADS resources"
    )
    ga4gh_vrs_allele: Optional[Allele] = None

    def __str__(self):
        if self.niagads_unique_id is not None:
            return self.niagads_unique_id
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
        if self.variant_class.is_structural_variant() and self.location.length is None:
            raise ValueError(
                "Must assign length of `structural variant` (`SV`) when initializing."
            )

        if self.variant_class in [VariantClass.SNV, VariantClass.SHORT_INS]:
            # SNV and SHORT_INS: length is 1
            self.location.length = 1
        else:  # MVN, SHORT_INDEL, SHORT_DEL length = length of ref
            self.location.length = len(self.ref)
        return self

    @model_validator(mode="after")
    def resolve_variant_type(self):

        len_ref = len(self.ref)
        len_alt = len(self.alt)
        if len_ref >= 50 or len_alt >= 50:
            # SV variant classes should have been set
            # at creation - FIXME: raise error?
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
    def from_positional_id(cls, variant_id: str):
        positional_id = variant_id.replace("-", ":")
        chrm, position, ref, alt = positional_id.split(":")
        start = position - 1  # GenomicRegions are 0-based
        location = GenomicRegion(
            chromosome=HumanGenome(chrm), start=start, length=start + len(ref)
        )
        return cls(
            location=location,
            ref=ref,
            alt=alt,
            positional_id=positional_id,
        )
