from typing import Optional, Self
from pydantic import  ConfigDict, field_serializer

from niagads.utils.enums import CustomStrEnum as StrEnum

from api.common.types import Range
from api.models.base_models import RowModel
from niagads.reference.chromosomes import Human

class Strand(StrEnum):
    SENSE = '+'
    ANTISENSE = '-'
    
    def __str__(self):
        return self.value

class GenomicRegion(RowModel, Range):
    chromosome: Human
    strand: Optional[Strand]
    
    # so that strand does not get returned if missing
    # so thta end does not get returned if missing (e.g, SNVs)
    model_config = ConfigDict(exclude_none=True)
    
    @field_serializer("chromosome")
    def serialize_group(self, chromosome: Human, _info):
        return str(chromosome)
    
    def __str__(self):
        span = f'{str(self.chromosome)}:{self.start}-{self.end}'
        if self.strand is not None:
            return f'{span:{str(self.strand)}}'
        else:
            return span

        
class Gene(RowModel):
    ensembl_id: str
    gene_symbol: str
    location: GenomicRegion

    
class Variant(RowModel):
    variant_id: str
    ref_snp_id: Optional[str]
    location: GenomicRegion