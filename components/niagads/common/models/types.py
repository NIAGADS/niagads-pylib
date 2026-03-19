from typing import Dict, Optional
from niagads.exceptions.core import ValidationError
from pydantic import BaseModel, Field, model_validator


class Range(BaseModel):
    start: int = Field(title="Start")
    end: Optional[int] = Field(default=None, title="End")

    def model_post_init(self, __context):
        if self.end is None:
            self.end = self.start

    @model_validator(mode="before")
    @classmethod
    def validate(self, range: Dict[str, int]):
        if "end" in range:
            if range["start"] > range["end"]:
                raise ValidationError(
                    f"Invalid Range: {range['start']} > {range['end']}"
                )
        return range

    def __str__(self):
        return f"{self.start}-{self.end}"

    def bracket_notation(self, inclusiveEnd: bool = False):
        return f"[{self.start}, {self.end}{']' if inclusiveEnd else ')'}"

    def is_valid_range(self, maxSpan: int):
        if self.end is None:
            raise RuntimeError("Range.end is None, cannot validate range size.")

        return self.end - self.start <= maxSpan
