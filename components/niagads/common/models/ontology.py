from typing import Optional

from niagads.common.models.core import TransformableModel
from pydantic import Field


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

    def __str__(self):
        return self.term

    def as_info_string(self):
        infoStr = f"term={self.term}"
        return (
            f"{infoStr};term_id={self.term_id}" if self.term_id is not None else infoStr
        )
