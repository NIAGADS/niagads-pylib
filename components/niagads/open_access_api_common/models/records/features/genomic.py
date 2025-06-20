from typing import Optional

from niagads.common.models.core import Range
from niagads.exceptions.core import ValidationError
from niagads.genome.core import GenomicFeatureType, Human, Strand
from niagads.open_access_api_common.models.records.core import RowModel
from niagads.utils.string import matches
from pydantic import (
    BaseModel,
    ConfigDict,
    Field,
    field_serializer,
    model_validator,
)


class GenomicRegion(RowModel, Range):
    chromosome: Human = Field(serialization_alias="chr")
    strand: Optional[Strand] = None

    # so that strand does not get returned if missing
    model_config = ConfigDict(exclude_none=True)

    @field_serializer("chromosome")
    def serialize_chromosome(self, chromosome: Human, _info):
        return str(chromosome)

    def __str__(self):
        span = f"{str(self.chromosome)}:{self.start}-{self.end}"
        if self.strand is not None:
            return f"{span:{str(self.strand)}}"
        else:
            return span


class GenomicFeature(BaseModel):
    feature_id: str
    feature_type: GenomicFeatureType

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
        pattern = r"^(?:[A-Za-z][A-Za-z0-9_.-]*(@)?|\d{5})$"  # matches symbols, ensembl ids, and entrez ids
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
        pattern = r".+:\d+-\d+$"  # chr:start-enddddd - NOTE: the r prefix declares the pattern as a raw string so that no syntax warning gets thrown for escaping the d

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
        pattern = r".+:\d+:[ACGT]+:[ACGT]+"

        if matches(pattern, id) == False:
            id = id.lower()
            pattern = r"rs\d+"
            if matches(pattern, id):
                return id
            else:
                raise ValidationError(
                    f"Invalid variant: `{id}`; please specify using the refSNP id or a positional allelic identifier (chr:pos:ref:alt)"
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
