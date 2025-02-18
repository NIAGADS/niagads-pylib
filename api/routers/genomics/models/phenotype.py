
from typing import List, Optional

from pydantic import BaseModel


# TODO: population -> ancestry/ethnic group
class Phenotype(BaseModel):
    population: Optional[List[str]]
    biomarker: Optional[str]
    genotype: Optional[str]
    Gender: Optional[str]
    
    