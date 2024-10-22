from fastapi.encoders import jsonable_encoder
from pydantic import BaseModel
from typing import Optional, Dict

class BiosampleCharacteristics(BaseModel):
    life_stage: Optional[str] = None
    biosample_term: Optional[str] = None
    system_category: Optional[str] = None
    tissue_category: Optional[str] = None
    biosample_display: Optional[str] = None
    biosample_summary: Optional[str] = None
    biosample_term_id: Optional[str] = None
