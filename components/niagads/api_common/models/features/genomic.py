from typing import Optional

from niagads.common.models.structures import Range
from niagads.exceptions.core import ValidationError
from niagads.genome.core import GenomicFeatureType, Human, Strand
from niagads.api_common.models.core import RowModel
from niagads.utils.regular_expressions import RegularExpressions
from niagads.utils.string import matches
from pydantic import (
    BaseModel,
    Field,
    field_serializer,
    model_validator,
)


class GenomicRegion(RowModel, Range):
    chromosome: Human = Field(serialization_alias="chr")
    length: Optional[int] = (
        None  # TODO -> calc length based on range if not set explicitly
    )
    strand: Optional[Strand] = Strand.SENSE

    def as_info_string(self):
        raise NotImplementedError("TODO when required")

    @field_serializer("chromosome")
    def serialize_chromosome(self, chromosome: Human, _info):
        return str(chromosome)

    @field_serializer("length")
    def serialize_length(self, length: str, _info):
        if length is None:
            return self.end - self.start

    def __str__(self):
        span = f"{str(self.chromosome)}:{self.start}-{self.end}"
        if self.strand is not None:
            return f"{span:{str(self.strand)}}"
        else:
            return span

    @classmethod
    def get_model_fields(cls, as_str=False):
        fields = super().get_model_fields()
        order = [
            "chr",  # have to use serialization alias
            "start",
            "end",
            "strand",
            "length",
        ]
        ordered_fields = {k: fields[k] for k in order}
        return list(ordered_fields.keys()) if as_str else ordered_fields


class GenomicFeature(BaseModel):
    feature_id: str
    feature_type: GenomicFeatureType

    def __str__(self):
        return self.feature_id

    @model_validator(mode="after")
    def validate_feature_id(self):
        if self.feature_type == GenomicFeatureType.VARIANT:
            self.feature_id = self.validate_variant_id(self.feature_id)

        if self.feature_type == GenomicFeatureType.SPAN:
            self.feature_id = self.validate_span(self.feature_id)

        if self.feature_type == GenomicFeatureType.GENE:
            self.validate_gene_id(self.feature_id)

        return self

    @staticmethod
    def validate_gene_id(id: str):
        pattern = RegularExpressions.GENE
        # check against regexp
        if matches(pattern, id):
            return id
        else:
            raise ValidationError(
                f"Invalid gene identifier: `{id}`;"
                f"please use Ensembl ID, Official Gene Symbol (case insensitive), or Entrez Gene ID"
            )

    @staticmethod
    def validate_span(span: str):
        pattern = r".+:\d+-\d+$"  # chr:start-enddddd

        # check against regexp
        if matches(pattern, span) == False:
            raise ValidationError(
                f"Invalid genomic span: `{span}`;"
                f"for a chromosome, N, please specify as chrN:start-end or N:start-end"
            )

        # split on :
        [chrm, coords] = span.split(":")
        try:
            validChrm = Human.validate(chrm)
        except KeyError:
            raise ValidationError(
                f"Invalid genomic span: `{span}`; invalid chromosome `{chrm}`"
            )

        # validate start < end
        [start, end] = coords.split("-")
        if int(start) > int(end):
            raise ValidationError(
                f"Invalid genomic span: `{span}`; start coordinate must be <= end"
            )

        return f"{validChrm}:{coords}"

    @staticmethod
    def validate_variant_id(id: str):
        pattern = RegularExpressions.VARIANT

        if matches(pattern, id) == False:
            pattern = RegularExpressions.REFSNP
            if matches(pattern, id.lower()):
                return id.lower()
            else:
                pattern = RegularExpressions.STRUCTUAL_VARIANT
                if matches(pattern, id.upper()):
                    return id.upper()
                else:
                    raise ValidationError(
                        f"Invalid variant: `{id}`; please specify using a refSNP id, a structural variant ID (e.g., DUP_CHR1_4AE4CDB8), or positional allelic identifier (chr:pos:ref:alt) with valid alleles: [A,C,G,T]"
                    )

        # validate chrm
        [chrm, pos, ref, alt] = id.split(":")
        try:
            Human.validate(chrm)
        except KeyError:
            raise ValidationError(
                f"Invalid genomic location: `{id}`; invalid chromosome `{chrm}`"
            )

        return id
