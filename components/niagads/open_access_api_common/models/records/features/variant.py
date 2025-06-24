from typing import Any, Dict, List, Optional, Literal, Union
from niagads.database.models.variant.composite_attributes import (
    PredictedConsequence,
    RankedConsequences,
)
from niagads.open_access_api_common.models.records.core import RowModel
from niagads.open_access_api_common.models.records.features.genomic import GenomicRegion
from niagads.open_access_api_common.models.response.core import GenericResponse
from pydantic import BaseModel, ConfigDict, Field, computed_field, field_serializer


class QCStatus(BaseModel):
    status_code: str  #  b/c there are some arbitrary codes
    passed: bool
    release: str


class VariantFeature(RowModel):
    variant_id: str = Field(title="Variant")
    ref_snp_id: Optional[str] = Field(default=None, title="Ref SNP ID")

    # should allow to fill from SQLAlchemy ORM model
    model_config = ConfigDict(from_attributes=True)


class Variant(VariantFeature):
    variant_class: str = Field(title="Variant Type")
    location: GenomicRegion
    length: int
    ref: str
    alt: Optional[str] = None


class AnnotatedVariant(Variant):
    is_adsp_variant: Optional[bool] = Field(
        default=False,
        title="Is ADSP Variant?",
        description="Variant present in ADSP samples and passed quality control checks; not an indicator of AD-risk.",
    )
    most_severe_consequence: Optional[PredictedConsequence] = Field(
        default=None,
        title="Predicted Consequence",
        description="most severe consequence predicted by VEP",
    )
    allele_string: str
    alternative_alleles: Optional[List[str]]
    colocated_variants: Optional[List[Variant]]

    is_multi_allelic: bool
    is_structural_variant: bool

    cadd_score: Optional[Dict[str, float]] = None
    adsp_qc: Optional[dict] = None

    allele_frequencies: Optional[dict] = None
    vep_predicted_consequences: Optional[RankedConsequences] = None
    associations: Optional[dict] = None

    @computed_field(
        default=None,
        title="ADSP QC Status",
        description="one of PASS, FAIL, or NA (if not variant not called via joint-genotype calling from ADSP sequencing data)",
    )
    @property
    def adsp_qc_status(self) -> Optional[List[QCStatus]]:
        if self.adsp_qc is None:
            return None
        else:
            statusList = []
            for release, scores in self.adsp_qc:
                status_code = self.adsp_qc["filter"]
                statusList.append(
                    QCStatus(
                        status_code=status_code,
                        passed="PASS" in status_code,
                        release=release,
                    )
                )

    passed_qc: bool
    release: str

    @field_serializer
    def serialize_adsp_qc(self, adsp_qc: Optional[dict], _info):
        if adsp_qc is None:
            return None

        qc = []
        for release, scores in adsp_qc:
            scores["release"] = release
            qc.append(scores)

        return qc


class AbridgedVariantResponse(GenericResponse):
    data: List[Variant]


class VariantResponse(GenericResponse):
    data: List[AnnotatedVariant]
