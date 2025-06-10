from typing import Any, Dict, List, Optional
from niagads.database.models.variant.composite_attributes import (
    PredictedConsequence,
    RankedConsequences,
)
from niagads.open_access_api_common.models.records.core import RowModel
from niagads.open_access_api_common.models.response.core import GenericResponse
from pydantic import ConfigDict, Field


class VariantFeature(RowModel):
    variant_id: str = Field(title="Variant")
    ref_snp_id: Optional[str] = Field(default=None, title="Ref SNP ID")

    # should allow to fill from SQLAlchemy ORM model
    model_config = ConfigDict(from_attributes=True)


class Variant(VariantFeature):
    type: str = Field(title="Variant Type")
    is_adsp_variant: Optional[bool] = Field(
        default=False,
        title="Is ADSP Variant?",
        description="Variant present in ADSP samples and passed quality control checks; not an indicator of AD-risk.",
    )
    most_severe_consequence: Optional[PredictedConsequence] = None
    # is_multi_allelic: bool


class AnnotatedVariant(Variant):
    length: str  # or location: GenomicRegion?
    cadd_score: Optional[Dict[str, float]] = None
    ADSP_qc: Optional[Dict[str, dict]] = None
    allele_frequencies: Optional[dict] = None
    predicted_consequences: Optional[RankedConsequences] = None


class VariantSummaryResponse(GenericResponse):
    data: List[Variant]


class AnnotatedVariantResponse(GenericResponse):
    data: List[AnnotatedVariant]
