from typing import Optional
from pydantic import  ConfigDict, field_serializer

from niagads.reference.chromosomes import Human

from api.common.enums.genome import Strand
from api.common.types import Range
from api.models.base_row_models import RowModel


class GenomicRegion(RowModel, Range):
    chromosome: Human
    strand: Optional[Strand] = None
    
    # so that strand does not get returned if missing
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
    
class Variant(RowModel):
    variant_id: str
    ref_snp_id: Optional[str] = None

    