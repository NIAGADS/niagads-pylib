from typing import Any, Dict, List, Optional, Self, Union

from niagads.common.models.core import TransformableModel
from pydantic import Field, model_validator


class OntologyTerm(TransformableModel):
    term: str = Field(
        title="Ontology Term",
        description="a term from a controlled vocabular or ontology",
    )
    term_id: Optional[str] = Field(
        default=None, title="Ontology Term ID", description="mapped ontology term ID"
    )
    ontology: Optional[str] = None
    term_iri: Optional[str] = Field(
        default=None,
        title="Ontology Term IRI",
        description="mapped ontology term IRI",
    )
    definition: Optional[str] = None

    @model_validator(mode="before")
    @classmethod
    def process_str(cls, data: Union[Dict[str, Any], str]):
        """create an OntologyTerm from just a term string"""
        if isinstance(data, str):
            return cls(term=data)

        if not isinstance(data, dict):
            data = data.model_dump()  # assume data is an ORM w/model_dump mixin

        return data

    def __str__(self):
        return self.term

    def as_info_string(self):
        infoStr = f"term={self.term}"
        return (
            f"{infoStr};term_id={self.term_id}" if self.term_id is not None else infoStr
        )
