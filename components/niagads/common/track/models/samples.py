from typing import List, Optional, Union

from niagads.common.models.base import CustomBaseModel
from niagads.common.reference.ontologies.models import OntologyTerm
from niagads.common.reference.ontologies.types import BiosampleType
from pydantic import Field, field_serializer

# TODO - how to handle biosample/biosample_type pairing, should we make another model?
# impact on metadata intake?


class BiosampleCharacteristics(CustomBaseModel):
    biosample: List[OntologyTerm] = Field(
        default=None,
        title="Biosample",
        description="ontology term describing the biosample",
    )
    biosample_type: Optional[List[BiosampleType]] = Field(
        default=None,
        title="Biosample: Type",
        description="the biological source of a sample used in an experiment",
    )
    biomarker: Optional[List[OntologyTerm]] = Field(default=None, title="Biomarker")
    system: Optional[List[str]] = Field(
        default=None,
        title="Biosample: Anatomical System",
        json_schema_extra={"is_filer_annotation": True},
    )
    tissue: Optional[List[OntologyTerm]] = Field(
        default=None,
        title="Biosample: Tissue",
        json_schema_extra={"is_filer_annotation": True},
    )

    life_stage: Optional[OntologyTerm] = Field(
        default=None,
        title="Biosample: Life Stage",
        description="donor or sample life stage",
        json_schema_extra={"is_filer_annotation": True},
    )

    @field_serializer("biosample_type")
    def serialize_biosample_type(self, value):
        """Serialize BiosampleType enum values to their model_dump representation."""
        if value is None:
            return None
        if isinstance(value, list):
            return [v.value.model_dump(exclude_none=True) for v in value]
        return value.value.model_dump(exclude_none=True)
