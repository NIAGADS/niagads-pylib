"""variant annotator functions"""

from niagads.enums.core import CaseInsensitiveEnum
from niagads.genomics.features.region.core import GenomicRegion
from niagads.genomics.sequence.chromosome import Human
from niagads.genomics.sequence.core import Assembly
from niagads.genomics.sequence.utils import reverse_complement
from niagads.utils.string import truncate, xstr
from pydantic import BaseModel, Field, model_validator


class VariantType(CaseInsensitiveEnum):
    SNV = "single-nucleotide variant"
    MNV = "multi-nucleotide variant"
    INDEL = "insertion-deletion"
    DEL = "deletion"
    INS = "insertion"
    SV = "structural variant"


class Variant(BaseModel, GenomicRegion):
    position: int
    ref: str
    alt: str
    ref_snp_id: str = None
    positional_id: str = None
    variant_type: VariantType = None
    verified: bool = False
    primary_key: str = Field(default=None, description="database primary key")

    @model_validator(mode="after")
    def resolve_span(self):
        return self._set_span()

    def _set_span(self):
        """
        Set start and end coordinates for the variant based on its type.
        """
        self.start = self.position

        l_ref = len(self.ref)
        if self.variant_type in [VariantType.SNV, VariantType.INS]:
            # SNV: start = end = position
            self.end = self.start
        elif self.variant_type == VariantType.MNV:
            # MNV: end = start + length - 1
            self.end = self.start + l_ref - 1
        elif self.variant_type == VariantType.DEL:
            # DEL: end = start + length(ref) - 1
            self.end = self.start + l_ref - 1
        elif self.variant_type == VariantType.INDEL:
            # INDEL: treat as deletion for span
            self.end = self.start + l_ref - 1
        elif self.variant_type == VariantType.SV:
            self.end = None
        return self

    @model_validator(mode="after")
    def resolve_variant_type(self):
        len_ref = len(self.ref)
        len_alt = len(self.alt)

        if len_ref >= 50 or len_alt >= 50:
            self.variant_type = VariantType.SV
        elif len_ref == 1 and len_alt == 1:
            self.variant_type = VariantType.SNV
        elif len_ref == len_alt and len_ref > 1:
            self.variant_type = VariantType.MNV
        elif len_ref == 0 and len_alt > 0:
            self.variant_type = VariantType.INS
        elif len_ref > 0 and len_alt == 0:
            self.variant_type = VariantType.DEL
        elif len_ref > 0 and len_alt > 0:
            self.variant_type = VariantType.INDEL

        return self

    @classmethod
    def from_positional_id(cls, positional_id):
        chrm, position, ref, alt = positional_id.split(":")
        start, end = cls._get_span(position, ref, alt)
        return cls(
            chromosome=Human(chrm),
            position=position,
            ref=ref,
            alt=alt,
            positional_id=positional_id,
        )

    def _get_span(self):
        """
        Infer the end location of a variant (span of indels/deletions).

        Returns:
            int: End location of the variant.
        """

        norm_ref, norm_alt = self._normalize_alleles()

        len_ref = len(self.ref)
        len_alt = len(self.alt)

        len_nref = len(norm_ref)
        len_nalt = len(norm_alt)

        position = int(self.position)

        if len_ref == 1 and len_alt == 1:  # SNV
            return position

        if len_ref == len_alt:  # MNV
            if self.ref == self.alt[::-1]:  # inversion
                return position + len_ref - 1

            # substitution
            return position + len_nref - 1

        if len_nalt >= 1:  # insertion
            if len_nref >= 1:  # indel
                return position + len_nref
            # e.g. CCTTAAT/CCTTAATC -> -/C but the VCF position is at the start and not where the ins actually happens
            elif len_nref == 0 and len_ref > 1:
                return position + len_ref - 1  # drop first base
            else:
                return position + 1

        # deletion
        if len_nref == 0:
            return position + len_ref - 1
        else:
            return position + len_nref


class VariantStandardizer(object):
    """
    this normalizes, generates primary keys, and validates, standardizes using ga4gh.vrs
    """

    def __init__(self, genome_build: Assembly, seqrepo_service_url: str):
        self._seqrepo_service_url = seqrepo_service_url
        self._genome_build = genome_build
