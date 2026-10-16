from typing import List, Union

from niagads.api.common.models.entities.variant.records import (
    Variant,
    VariantBrief,
    VariantDescriptor,
)
from niagads.api.common.models.responses.data import DataResponse
from niagads.utils.list import qw
from niagads.utils.regular_expressions import RegularExpressions
from niagads.utils.string import matches

VCF_FIELDS = qw("CHROM POS ID REF ALT QUAL FILTER INFO")
VCF_FIELDS_LOWER = [f.lower() for f in VCF_FIELDS]
VCF_VALUE_TEMPLATE = ["."] * len(VCF_FIELDS)


class VariantResponse(DataResponse):
    data: List[Union[VariantDescriptor, VariantBrief, Variant]]

    @staticmethod
    def _is_structural_variant(record: Union[VariantDescriptor, VariantBrief, Variant]):
        if isinstance(record, Variant):
            return record.is_structural_variant
        else:
            return not matches(record.id, RegularExpressions.POSITIONAL_VARIANT_ID)

    @staticmethod
    def _to_vcf_entry(
        record: Union[VariantDescriptor, VariantBrief, Variant], as_text: bool = False
    ) -> dict:
        """Note only works when record is not a structural variant for now"""

        chrm, pos, ref, alt = record.id.split(":")
        id = record.ref_snp_id if record.ref_snp_id is not None else record.id
        # TODO: Need to decide which fields go into INFO string; depends on record model
        vcf_values = [str(chrm), int(pos), id, ref, alt, ".", ".", "."]
        return dict(zip(VCF_FIELDS_LOWER, vcf_values))

    def to_vcf(self, as_text: bool = False):
        """ """
        # TODO: handle stuctural variants.  Only possible w/variant records for now

        if not self.data:
            return []

        vcf_entries = [
            self._to_vcf_entry(record, as_text)
            for record in self.data
            if not self._is_structural_variant(record)
        ]

        if as_text:
            return "\n".join(
                ["#" + "\t".join(VCF_FIELDS)]
                + ["\t".join(entry) for entry in vcf_entries]
            )
        else:
            return vcf_entries

    def to_delimited_text(
        self, *, fields=None, incl_header=False, null_str="NA", delimiter="\t"
    ):
        # TODO need to decide which fields to promote for response; probably
        # same a INFO in VCF repsonse

        raise NotImplementedError(
            "Coming Soon: not yet implemented for a variant record."
        )


class VariantAssociationResponse(DataResponse): ...
