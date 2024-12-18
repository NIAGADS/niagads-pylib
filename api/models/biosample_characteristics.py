from pydantic import Field
from typing import Optional

from .base_models import SerializableModel

class BiosampleCharacteristics(SerializableModel):
    system_category: Optional[str] = None
    tissue_category: Optional[str] = None
    # biosample_display: Optional[str] = None
    # biosample_summary: Optional[str] = None
    biosample_term: Optional[str] = Field(default=None, description='mapped ontology term')
    biosample_term_id: Optional[str] = Field(default=None, description='mapped ontology term identifier')
    life_stage: Optional[str] = Field(default=None, description='donor/sample life stage: adult, fetal, embryo')
    

    
    