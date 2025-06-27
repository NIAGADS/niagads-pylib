from typing import Optional

from niagads.common.models.core import NullFreeModel
from pydantic import Field


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
