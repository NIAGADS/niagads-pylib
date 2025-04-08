from enum import auto
from typing import Dict, List, Optional, Union
from pydantic import BaseModel

from api.common.enums.base_enums import CaseInsensitiveEnum

# TODO: population -> ancestry/ethnic group

class Phenotype(BaseModel):
    population: Optional[str] = None
    biomarker: Optional[str] = None
    genotype: Optional[str] = None
    gender: Optional[str] = None
    disease: Optional[str] = None
    neuropathology: Optional[str] = None


# FIXME: check NG00048_GRCh38 which has no control counts
class StudyGroup(BaseModel):
    group: str 
    num_samples: Optional[Union[int, Dict[str, int]]] = None