from typing import Dict, Optional
from niagads.utils.dict import prune
from pydantic import BaseModel, Field, model_serializer, model_validator


class NullFreeModel(BaseModel):
    """a pydantic model where attributes with NULL values (e.g., None, 'NULL') are removed during serialization"""

    @model_serializer()
    def serialize_model(self, values, **kwargs):
        return prune(dict(self), removeNulls=True)


class OntologyTerm(NullFreeModel):
    term: str = Field(
        title="Biosample", description="ontology term describing biosample material"
    )
    term_id: Optional[str] = Field(
        default=None, title="Biosample: Term ID", description="mapped ontology term ID"
    )
    ontology: Optional[str] = None
    term_iri: Optional[str] = Field(
        default=None,
        title="Biosample: Term IRI",
        description="mapped ontology term IRI",
    )
    definition: Optional[str] = None

    def __str__(self):
        return self.term


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
