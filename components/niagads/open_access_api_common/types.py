from enum import auto
from typing import Annotated, Any, Dict, List, Optional, Union

from niagads.enums.core import CaseInsensitiveEnum
from niagads.utils.regular_expressions import RegularExpressions
from pydantic import BaseModel, Field, model_validator

T_JSON = Union[Dict[str, Any], List[Any], int, float, str, bool, None]

T_PubMedID = Annotated[str, Field(pattern=RegularExpressions.PUBMED_ID)]


class RecordType(CaseInsensitiveEnum):
    GENE = auto()
    VARIANT = auto()
    # STRUCTURAL_VARIANT = auto()
    SPAN = auto()
    TRACK = auto()

    def __str__(self):
        return self.name.lower()


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
