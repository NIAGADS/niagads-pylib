from typing import ClassVar, Optional

from niagads.common.models.types import Range
from niagads.genome_reference.human import HumanGenome
from niagads.genome_reference.types import Strand
from pydantic import Field, field_serializer


class GenomicRegion(Range):
    """
    Model representing a genomic region. Defaults to 1-based (inclusize_end = True)

    Attributes:
        chromosome (HumanGenome): Chromosome name.
        start (int): Start position (1-based, inclusive).
        end (int): End position (1-based, inclusive).
        length (Optional[int]): Length of the region.
        strand (Optional[Strand]): DNA strand.
        inclusive_end (bool): Whether the end coordinate is inclusive.
    """

    chromosome: HumanGenome = Field(title="Chromosome", serialization_alias="chr")
    length: Optional[int] = Field(default=None, title="Length")
    strand: Optional[Strand] = Field(default=Strand.SENSE, title="Strand")
    inclusive_end: Optional[bool] = Field(default=True)

    @classmethod
    def from_region_id(cls, span: str):
        chromosome, range = span.split(":")
        start, end = range.split("-")
        return cls(chromosome=HumanGenome(chromosome), start=start, end=end)

    @field_serializer("chromosome")
    def serialize_chromosome(self, chromosome: HumanGenome, _info):
        return str(chromosome)

    @field_serializer("length")
    def serialize_length(self, length: str, _info):
        if length is None:
            if self.inclusive_end:
                return self.end - self.start + 1
            return self.end - self.start
        return length

    def __str__(self):
        span = f"{str(self.chromosome)}:{self.start}-{self.end}"
        if self.strand is not None:
            return f"{span}:{str(self.strand)}"
        else:
            return span


class OneBasedGenomicRegion(GenomicRegion):
    inclusive_end: ClassVar[bool] = True

    @classmethod
    def from_zero_based_region(cls, region: GenomicRegion) -> GenomicRegion:
        """
        Convert a ZeroBasedGenomicRegion to a OneBasedGenomicRegion.

        Args:
            region (ZeroBasedGenomicRegion): The zero-based region to convert.

        Returns:
            OneBasedGenomicRegion: The converted 1-based region.
        """

        if region.inclusive_end:
            return region  # already 1-based

        return cls(
            chromosome=region.chromosome,
            start=region.start + 1,
            end=region.end,
            length=region.length,
            strand=region.strand,
        )


class ZeroBasedGenomicRegion(GenomicRegion):
    inclusive_end: ClassVar[bool] = False

    @classmethod
    def from_one_based_region(cls, region: GenomicRegion) -> GenomicRegion:
        """
        Convert a 1-based GenomicRegion to a ZeroBasedGenomicRegion.

        Args:
            region (GenomicRegion): The 1-based region to convert.

        Returns:
            ZeroBasedGenomicRegion: The converted 0-based region.
        """

        if not region.inclusive_end:  # already 0-based
            return region

        return cls(
            chromosome=region.chromosome,
            start=region.start - 1,
            end=region.end,
            length=region.length,
            strand=region.strand,
        )
