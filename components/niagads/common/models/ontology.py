"""
Ontology term and relationship models for GenomicsDB ETL plugins.

Defines Pydantic models for representing ontology terms and RDF relationships
in the reference ontology graph schema. Used for metadata extraction,
validation, and graph construction in ontology loader plugins.
"""

from typing import Optional, Union
from niagads.common.models.core import TransformableModel
from niagads.utils.regular_expressions import RegularExpressions
from niagads.utils.string import dict_to_info_string, matches, to_snake_case
from pydantic import BaseModel, Field, field_validator, model_validator


class OntologyTerm(TransformableModel):
    """
    Pydantic model representing a term in an ontology graph.

    Used for storing ontology term metadata, including category, label,
    definition, synonyms, and obsolescence information.
    """

    term_iri: Optional[str] = Field(
        default=None,
        description="globally unique identifier for the ontology term (URI)",
    )
    term_id: Optional[str] = Field(
        default=None, description="unique, stable local identifier"
    )
    term: str = Field(..., description="the ontology term")

    label: Optional[str] = Field(
        default=None, description="Human-readable label for the term"
    )
    definition: Optional[str] = Field(
        default=None, description="Textual definition of the term"
    )
    synonyms: list[str] = Field(
        default_factory=list, description="List of synonyms for the term"
    )
    is_deprecated: bool = Field(
        default=False, description="True if the term is deprecated"
    )
    is_placeholder: bool = Field(default=False, description="True if palceholder term")

    @staticmethod
    def extract_term_id(iri: str) -> str:
        return iri.rsplit("/", 1)[-1].replace("_", ":")

    @field_validator("term_id", mode="before")
    def validate_term_id(cls, v, data: dict):
        """
        Validate ID for the ontology term. If term_id is None,
        extracts it from the URI. Raises a validation error if both are None.
        """
        if v is not None:
            return v
        term_iri: str = data.get("term_iri")
        if term_iri:
            return cls.extract_term_id(term_iri)

        raise ValueError(
            "Either 'term_id' or 'term_iri' must be provided for OntologyTerm."
        )

    @model_validator(mode="before")
    def normalize_field_values(cls, values: Union[str, dict]):
        """
        Converts all non-boolean field values to strings before model validation.

        Args:
            values (dict): Dictionary of field values.

        Returns:
            dict: Updated field values with non-boolean values converted to strings.
        """

        # if trying to serialize a string as an ontology term, assume
        # it is the term or term_id
        if isinstance(values, str):
            if matches(values, RegularExpressions.ONTOLOGY_TERM_ID):
                term_id = values.replace("_", ":")
                return cls(term_id=term_id, term=term_id)
            return cls(term=values)

        for field, v in values.items():
            if v is not None and not isinstance(v, bool):
                if field == "term_id":
                    values[field] = str(v).replace("_", ":")
                else:
                    values[field] = str(v)
        return values

    def __str__(self):
        return self.term

    def as_info_string(self) -> str:
        info: dict = {"term": self.term}
        if self.term_id:
            info.update({"term_id": self.term_id})
        return dict_to_info_string(info)


class OntologyTriple(BaseModel):
    """
    Pydantic model representing an RDF triple in the ontology graph.

    Each triple consists of a subject, predicate, and object URI or value.
    """

    subject: str
    predicate: str
    object: str

    def __str__(self):
        return dict_to_info_string(self.model_dump())
