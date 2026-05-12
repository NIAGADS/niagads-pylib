"""variant annotator functions"""

from typing import Optional

from niagads.common.genomic.regions.models import OneBasedGenomicRegion
from niagads.common.models.base import CustomBaseModel
from niagads.common.models.types import Range
from niagads.common.variant.models.ga4gh_vrs import Allele
from niagads.common.variant.types import VariantClass
from niagads.genome_reference.human import HumanGenome
from niagads.utils.regular_expressions import RegularExpressions
from pydantic import Field, model_validator

# TODO: add ga4gh to variant identifier (optional? maybe)


class VariantIdentifier(CustomBaseModel):
    ref_snp_id: Optional[str] = Field(
        default=None, pattern=RegularExpressions.REF_SNP_ID
    )
    id: str = Field(
        pattern=RegularExpressions.POSITIONAL_VARIANT_ID
        + "|"
        + RegularExpressions.STRUCTUAL_VARIANT_ID,
        description="stable NIAGADS variant ID",
    )


class VariantRecord(VariantIdentifier):
    chromosome: HumanGenome
    position: int
    length: Optional[int] = None
    ref: str
    alt: str
    variant_class: VariantClass = Field(default=VariantClass.SNV)

    ga4gh_vrs: Optional[Allele] = None

    positional_id: Optional[str] = None
    normalized_positional_id: Optional[str] = Field(
        default=None, pattern=RegularExpressions.NORMALIZED_POSITIONAL_VARIANT_ID
    )

    def __str__(self):
        if self.id is not None:
            return self.id
        else:
            if self.variant_class.is_structural_variant():
                return (
                    f"{self.location.chromosome.value}:{self.location.start}/"
                    f"{self.variant_class}:{self.location.length}"
                )
            else:
                return self.positional_id

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
        elif len_ref == 1 and len_alt > 0:
            self.variant_class = VariantClass.SHORT_INS
        elif len_ref > 0 and len_alt == 1:
            self.variant_class = VariantClass.SHORT_DEL
        elif len_ref > 0 and len_alt > 0:
            self.variant_class = VariantClass.SHORT_INDEL

        return self

    @model_validator(mode="after")
    def resolve_length(self):
        return self._resolve_length()

    @property
    def span(self):
        return Range(
            start=self.position, end=self.position + self.length - 1, inclusive_end=1
        )

    @property
    def genomic_region(self):
        return OneBasedGenomicRegion(
            **self.span.model_dump(), chromosome=self.chromosome, length=self.length
        )

    def _resolve_length(self):
        """
        Determine variant length based on type and length of reference allele
        helper function created b/c needs to be done at initialization and then recalculated
        after normalization
        """
        if self.variant_class.is_structural_variant() and self.location.length is None:
            # assume generic INDEL
            self.length = max(len(self.ref), len(self.alt))

        if self.variant_class in [VariantClass.SNV, VariantClass.SHORT_INS]:
            # SNV and SHORT_INS: length is 1
            self.length = 1
        else:  # MVN, SHORT_INDEL, SHORT_DEL length = length of ref
            self.length = len(self.ref)
        return self

    @classmethod
    def from_positional_id(cls, variant_id: str):
        positional_id = variant_id.replace("-", ":")
        chrm, position, ref, alt = positional_id.split(":")

        return cls(
            chromosome=HumanGenome(chrm),
            position=position,
            ref=ref,
            alt=alt,
            positional_id=positional_id,
            id=positional_id,
        )
