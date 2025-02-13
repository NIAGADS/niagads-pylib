from typing import Optional
from pydantic import ConfigDict, field_serializer
from api.models.base_models import SerializableModel
from niagads.reference.chromosomes import Human

class Region(SerializableModel):
    chromosome: Human
    start: int
    end: int
    
    @field_serializer("chromosome")
    def serialize_group(self, chromosome: Human, _info):
        return str(chromosome)
    
    def __str__(self):
        return f'{str(self.chromosome)}:{self.start}-{self.end}'
        
        
class Gene(SerializableModel):
    ensembl_id: str
    gene_symbol: str

    
class Variant(SerializableModel):
    variant_id: str
    ref_snp_id: Optional[str]