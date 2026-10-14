from typing import List, Optional, Union

from niagads.api.common.models.records.base import ORMCompatibleRecord
from niagads.common.variant.models.annotations import PredictedConsequenceSummary
from niagads.common.variant.models.record import VariantIdentifier, VariantRecord
from pydantic import ConfigDict, Field, field_validator, model_validator


class VariantDescriptor(VariantIdentifier): ...


class VariantBrief(VariantDescriptor, ORMCompatibleRecord):
    model_config = ConfigDict(is_summary=True)

    variant_class: str = Field(title="Variant Type")
    is_adsp_variant: Optional[bool] = Field(
        default=False,
        title="Is ADSP Variant?",
        description="Variant present in ADSP samples and passed quality control checks; not an indicator of AD-risk.",
    )

    most_severe_consequence: Optional[PredictedConsequenceSummary] = Field(
        default=None,
        title="Predicted Consequence",
        description="most severe consequence predicted by VEP",
    )

    @field_validator("is_adsp_variant", mode="before")
    @classmethod
    def set_is_adsp_variant(cls, v):
        return cls.boolean_null_check(v)

    @field_validator("most_severe_consequence", mode="before")
    @classmethod
    def extract_most_severe_conseqeunce(cls, v):
        if v is None:
            return None
        if not isinstance(v, dict):  # ORM response
            v = v.model_dump()
        if "impacted_gene" in v:
            return PredictedConsequenceSummary(**v)
        else:
            return PredictedConsequenceSummary.from_vep_json(v)


class Variant(VariantRecord, ORMCompatibleRecord): ...
