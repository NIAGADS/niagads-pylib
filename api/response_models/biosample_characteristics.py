from fastapi.encoders import jsonable_encoder
from pydantic import BaseModel
from typing import Optional, Dict

class BiosampleCharacteristics(BaseModel):
    life_stage: Optional[str]
    biosample_term: Optional[str]
    system_category: Optional[str]
    tissue_category: Optional[str]
    biosample_display: Optional[str]
    biosample_summary: Optional[str]
    biosample_term_id: Optional[str]
