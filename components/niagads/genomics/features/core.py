from enum import auto

from niagads.common.models.structures import Range
from niagads.enums.core import CaseInsensitiveEnum
from niagads.genomics.sequence.assembly import HumanGenome
from niagads.utils.regular_expressions import RegularExpressions
from niagads.utils.string import matches
from pydantic import BaseModel, model_validator


class GenomicFeatureType(CaseInsensitiveEnum):
    GENE = auto()
    VARIANT = auto()
    STRUCTURAL_VARIANT = auto()
    REGION = auto()


class GenomicFeature(BaseModel):
    feature_id: str
    feature_type: GenomicFeatureType

    def __str__(self):
        return self.feature_id

    @model_validator(mode="after")
    def validate_feature_id(self):
        if self.feature_type == GenomicFeatureType.VARIANT:
            self.feature_id = self.validate_variant_id(self.feature_id)

        if self.feature_type == GenomicFeatureType.REGION:
            self.feature_id = self.validate_span(self.feature_id)

        if self.feature_type == GenomicFeatureType.GENE:
            self.validate_gene_id(self.feature_id)

        return self

    def is_within_range_limit(self, maxSpan: int):
        if self.feature_type != GenomicFeatureType.REGION:
            raise RuntimeError(
                "Attempting to validate region size for feature of non-REGION type"
            )

        chrm, span = self.feature_id.split(":")
        start, end = span.split("-")
        spanRange = Range(start=start, end=end)
        return spanRange.is_valid_range(maxSpan)

    @staticmethod
    def validate_gene_id(id: str):
        pattern = RegularExpressions.GENE
        # check against regexp
        if matches(pattern, id):
            return id
        else:
            raise ValueError(
                f"Invalid gene identifier: `{id}`;"
                f"please use Ensembl ID, Official Gene Symbol (case insensitive), or Entrez Gene ID"
            )

    @staticmethod
    def validate_span(span: str):
        # Check if the number of dashes in the span is greater than 1
        # b/c path parameter can possibly be chrN-start-end
        if span.count("-") > 1:
            span = span.replace("-", ":", 1)

        pattern = r".+:\d+-\d+$"  # chr:start-enddddd

        # check against regexp
        if matches(pattern, span) == False:
            raise ValueError(
                f"Invalid genomic span: `{span}`;"
                f"for a chromosome, N, please specify as chrN:start-end or N:start-end"
            )

        # split on :
        [chrm, coords] = span.split(":")
        try:
            validChrm = HumanGenome.validate(chrm, inclPrefix=False)
        except KeyError:
            raise ValueError(
                f"Invalid genomic span: `{span}`; invalid chromosome `{chrm}`"
            )

        # validate start < end
        [start, end] = coords.split("-")
        if int(start) > int(end):
            raise ValueError(
                f"Invalid genomic span: `{span}`; start coordinate must be <= end"
            )

        return f"{validChrm}:{coords}"

    @staticmethod
    def validate_variant_id(id: str):
        pattern = RegularExpressions.POSITIONAL_VARIANT_ID

        if matches(pattern, id) == False:
            pattern = RegularExpressions.REFSNP
            if matches(pattern, id.lower()):
                return id.lower()
            else:
                pattern = RegularExpressions.STRUCTUAL_VARIANT
                if matches(pattern, id.upper()):
                    return id.upper()
                else:
                    raise ValueError(
                        f"Invalid variant: `{id}`; please specify using a refSNP id, a structural variant ID (e.g., DUP_CHR1_4AE4CDB8), or positional allelic identifier (chr:pos:ref:alt) with valid alleles: [A,C,G,T]"
                    )

        # validate chrm
        [chrm, pos, ref, alt] = id.split(":")
        try:
            HumanGenome.validate(chrm)
        except KeyError:
            raise ValueError(
                f"Invalid genomic location: `{id}`; invalid chromosome `{chrm}`"
            )

        return id
