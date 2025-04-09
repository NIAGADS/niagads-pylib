from typing import Any, Dict, List, Optional, Union
from pydantic import BaseModel, model_validator


T_JSON = Union[Dict[str, Any], List[Any], int, float, str, bool, None]


class Range(BaseModel):
    start: int
    end: Optional[int] = None

    def model_post_init(self, __context):
        if self.end is None:
            self.end = self.start

    @model_validator(mode="before")
    @classmethod
    def validate(self, range: Dict[str, int]):
        if "end" in range:
            if range["start"] > range["end"]:
                raise RuntimeError(f"Invalid Range: {range['start']} > {range['end']}")
        return range
