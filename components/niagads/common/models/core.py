from typing import Dict, Optional
from niagads.common.core import NullFreeModel
from pydantic import BaseModel, model_validator


class OntologyTerm(NullFreeModel):
    term: str
    term_id: Optional[str] = None
    ontology: Optional[str] = None
    term_iri: Optional[str] = None
    defintion: Optional[str] = None


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
