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

    @property
    def range(self):
        return Range(start=self.start, end=self.end, inclusive_end=self.inclusive_end)

    @classmethod
    def from_region_id(cls, span: str, is_zero_based: bool = False):
        """
        Create a GenomicRegion from a region string in the format 'chr:start-end:strand'.

        Args:
            span (str): Region string, e.g., '1:100-200'.
            is_zero_based (bool): If True, interpret coordinates as 0-based (start inclusive, end exclusive). If False, interpret as 1-based (start and end inclusive).

        Returns:
            GenomicRegion: Parsed region object with correct coordinate convention.
        """
        positional_elements = span.split(":")  # chrm, range, strand (optional)
        start, end = positional_elements[1].split("-")
        start = int(start)
        end = int(end)

        range = cls(
            chromosome=HumanGenome(positional_elements[0]),
            start=start,
            end=end,
            inclusive_end=not is_zero_based,
        )

        if len(positional_elements) == 3:
            range.strand = positional_elements[2]

        return range

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

    def to_zero_based_region(self) -> "ZeroBasedGenomicRegion":
        """
        Convert this OneBasedGenomicRegion to a ZeroBasedGenomicRegion.

        Returns:
            ZeroBasedGenomicRegion: The converted 0-based region.
        """

        return ZeroBasedGenomicRegion(
            chromosome=self.chromosome,
            start=self.start - 1,
            end=self.end,
            length=self.length,
            strand=self.strand,
        )


class ZeroBasedGenomicRegion(GenomicRegion):
    inclusive_end: ClassVar[bool] = False

    def to_one_based_region(self) -> "OneBasedGenomicRegion":
        """
        Convert this ZeroBasedGenomicRegion to a OneBasedGenomicRegion.

        Returns:
            OneBasedGenomicRegion: The converted 1-based region.
        """

        return OneBasedGenomicRegion(
            chromosome=self.chromosome,
            start=self.start + 1,
            end=self.end,
            length=self.length,
            strand=self.strand,
        )
