from typing import List, Optional, Set

from niagads.common.models.core import TransformableModel
from pydantic import Field


class ExperimentalDesign(TransformableModel):
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
    data_category: Optional[str] = Field(default=None, title="Data Category")
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
    covariates: Optional[List[str]] = Field(default=None, title="Covariates")

    def __str__(self):
        return self.as_info_string()

    def _flat_dump(self, nullFree=False, delimiter="|"):
        obj = super()._flat_dump(nullFree, delimiter=delimiter)
        if self.covariates is not None:
            obj["covarites"] = self._list_to_string(
                self.covariates, delimiter=delimiter
            )
        return obj
