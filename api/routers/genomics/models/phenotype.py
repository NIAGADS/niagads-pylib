
from typing import List, Optional
from api.models.base_models import SerializableModel

# TODO: population -> ancestry/ethnic group
class Phenotype(SerializableModel):
    population: Optional[List[str]]
    biomarker: Optional[str]
    genotype: Optional[str]
    Gender: Optional[str]
    
    