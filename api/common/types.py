from typing import Optional
from pydantic import BaseModel, model_validator

class Range(BaseModel):
    start: int
    end: int
    
    @model_validator(mode="before")
    def validate(self):
        if self.start > self.end:
            raise RuntimeError(f'Invalid Range: {self.start} > {self.end}')