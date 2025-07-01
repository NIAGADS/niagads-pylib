from typing import Optional

from niagads.common.models.core import CustomBaseModel
from pydantic import Field


class OntologyTerm(CustomBaseModel):
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

    def as_table_row(self):
        return {k: getattr(self, k) for k in self.view_fields(asStr=True)}

    @classmethod
    def table_fields(self, asStr: bool = False):
        return (
            list(self.__class__.model_fields.keys())
            if asStr
            else self.__class__.model_fields
        )

    def as_list(self, fields=None):
        if fields is None:
            return list(self.model_dump().values())
        else:
            return [v for k, v in self.model_dump() if k in fields]
