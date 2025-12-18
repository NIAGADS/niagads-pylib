from typing import Optional

from niagads.common.models.structures import Range
from niagads.genomics.sequence.chromosome import Human
from niagads.genomics.sequence.core import Strand
from pydantic import Field, field_serializer


class GenomicRegion(Range):
    chromosome: Human = Field(title="Chromosome", serialization_alias="chr")
    length: Optional[int] = Field(default=None, title="Length")
    strand: Optional[Strand] = Field(default=Strand.SENSE, title="Strand")
    max_range_size: Optional[int] = Field(default=None, exclude=True)

    @classmethod
    def from_region_id(cls, span):
        chromosome, range = span.split(":")
        start, end = range.split("-")
        return cls(chromosome=Human(chromosome), start=start, end=end)

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
