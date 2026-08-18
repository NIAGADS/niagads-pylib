from typing import List, Optional, Union

from niagads.api.common.models.records.base import ORMCompatibleRecord
from niagads.api.common.models.records.mixins import DynamicMixin, ORMCompatabileMixin
from niagads.common.models.base import CustomBaseModel
from niagads.common.variant.models.annotations import PredictedConsequenceSummary
from niagads.common.variant.models.record import VariantIdentifier, VariantRecord
from pydantic import Field, field_validator


class VariantDescriptor(VariantIdentifier, ORMCompatabileMixin): ...


class Variant(VariantRecord, ORMCompatabileMixin):
    positional_id: Optional[str] = Field(exclude=True)
    normalized_positional_id: Optional[str] = Field(exclude=True)


class AnnotatedVariantBrief(Variant):
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
    def parse_is_adsp_variant(cls, v):
        return cls.boolean_null_check(v)

    @field_validator("most_severe_consequence", mode="before")
    @classmethod
    def parse_most_severe_consequence(cls, v):
        if v is None:
            return None
        if not isinstance(v, dict):  # ORM response
            v = v.model_dump()
        if "impacted_gene" in v:
            return PredictedConsequenceSummary(**v)
        else:
            return PredictedConsequenceSummary.from_vep_json(v)


class AnnotatedVariant(AnnotatedVariantBrief):

    # FIXME: these queries can take a while; not part of the variant record
    # alternative_alleles: Optional[List[str]]
    # colocated_variants: Optional[List[Variant]]

    allele_frequencies: Optional[dict] = Field(
        default=None, description="allele frequencies from 1000Genomes, ALFA, ExAC"
    )
    adsp_annotation: Optional[dict] = Field(
        default=None,
        description="ADSP Annotation (see FAQ): incl. ranked VEP most severe consequence; selected FAVOR annotations",
    )

    vep_annotation: Optional[dict] = Field(
        default=None,
        description="full VEP annotation (w/out ADSP ranking; see FAQ)",
    )


class VariantAnnotation(ORMCompatibleRecord, DynamicMixin): ...
