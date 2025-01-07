from typing import Dict
from pydantic import BaseModel, model_validator

class Range(BaseModel):
    start: int
    end: int
    
    @model_validator(mode="before")
    @classmethod
    def validate(self, range: Dict[str, int]):
        if range['start'] > range['end']:
            raise RuntimeError(f"Invalid Range: {range['start']} > {range['end']}")
        return range