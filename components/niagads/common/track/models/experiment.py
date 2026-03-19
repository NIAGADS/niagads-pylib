from typing import List, Optional, Set

from niagads.common.models.base import CustomBaseModel
from niagads.common.reference.ontologies.models import OntologyTerm
from pydantic import Field


class ExperimentalDesign(CustomBaseModel):
    antibody_target: Optional[str] = Field(
        default=None,
        title="Antibody Target",
        json_schema_extra={"is_filer_annotation": True},
    )
    assay: Optional[str] = Field(
        default=None,
        title="Assay",
        json_schema_extra={"is_filer_annotation": True},
    )
    analysis: Optional[str] = Field(default=None, title="Analysis")
    classification: Optional[str] = Field(
        default=None,
        title="Classification",
        json_schema_extra={"is_filer_annotation": True},
    )
    data_category: Optional[OntologyTerm] = Field(default=None, title="Data Category")
    output_type: Optional[str] = Field(
        default=None,
        title="Output Type",
        json_schema_extra={"is_filer_annotation": True},
    )
    is_lifted: Optional[bool] = Field(
        default=None,
        title="Is Lifted?",
        description="data are lifted from earlier genome build",
    )
    covariates: Optional[List[OntologyTerm]] = Field(default=None, title="Covariates")
