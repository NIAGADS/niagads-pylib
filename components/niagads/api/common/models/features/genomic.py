from typing import List, Optional, Union

from niagads.api.common.models.response.core import RecordResponse
from niagads.common.models.structures import Range
from niagads.exceptions.core import ValidationError
from niagads.sequence.types import GenomicFeatureType, Strand
from niagads.sequence.chromosome import Human
from niagads.api.common.models.core import RowModel
from niagads.utils.regular_expressions import RegularExpressions
from niagads.utils.string import matches
from pydantic import (
    BaseModel,
    Field,
    field_serializer,
    model_validator,
)


class GenomicRegion(RowModel, Range):
    chromosome: Human = Field(title="Chromosome", serialization_alias="chr")
    length: Optional[int] = Field(default=None, title="Length")
    strand: Optional[Strand] = Field(default=Strand.SENSE, title="Strand")
    max_range_size: Optional[int] = Field(default=None, exclude=True)

    @classmethod
    def from_region_id(cls, span):
        chromosome, range = span.split(":")
        start, end = range.split("-")
        return cls(chromosome=Human(chromosome), start=start, end=end)

    def as_info_string(self):
        raise NotImplementedError("TODO when required")

    @field_serializer("chromosome")
    def serialize_chromosome(self, chromosome: Human, _info):
        return str(chromosome)

    @field_serializer("length")
    def serialize_length(self, length: str, _info):
        if length is None:
            return self.end - self.start
        return length

    def __str__(self):
        span = f"{str(self.chromosome)}:{self.start}-{self.end}"
        # if self.strand is not None:
        #    return f"{span}:{str(self.strand)}"
        # else:
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
            raise ValidationError(
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
            raise ValidationError(
                f"Invalid genomic span: `{span}`;"
                f"for a chromosome, N, please specify as chrN:start-end or N:start-end"
            )

        # split on :
        [chrm, coords] = span.split(":")
        try:
            validChrm = Human.validate(chrm, inclPrefix=False)
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


class AnnotatedGenomicRegion(RowModel):
    id: str = Field(title="Region ID")
    location: GenomicRegion
    # gc_content: float = Field(
    #    default=None,
    #    title="GC Content %",
    #    description="proportion of guanine (G) and cytosine (C) bases in a DNA sequence, indicating its nucleotide composition and stability",
    # )
    num_structural_variants: int = Field(
        title="Num. Strucutral Variants",
        description="number of SVs contained within or overlapping the region",
    )
    num_genes: int = Field(
        title="Num. Genes",
        description="number of genes contained within or overlapping the region",
    )
    num_small_variants: Union[int, str] = Field(
        title="Num. Small Variants",
        description=f"number of SNVs, MVNs, and short INDELs (<50bp) contained within or overlapping the region; for regions > 50,000bp this number is not calculated",
    )

    # TODO: need to host and acces the FASTA fle to do this
    # @field_validator("gc_content", mode="before")
    # @classmethod
    # def calculate_gc_content(cls, v):
    #    gc_fraction()


class RegionResponse(RecordResponse):
    data: List[AnnotatedGenomicRegion]
