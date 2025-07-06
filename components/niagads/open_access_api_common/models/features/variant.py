from typing import List, Optional
from niagads.database.schemas.variant.composite_attributes import (
    CADDScore,
    PredictedConsequence,
    QCStatus,
    RankedConsequences,
)

from niagads.open_access_api_common.models.core import RowModel
from niagads.open_access_api_common.models.features.genomic import GenomicRegion
from niagads.open_access_api_common.models.response.core import RecordResponse
from pydantic import (
    ConfigDict,
    Field,
    field_validator,
)


class VariantFeature(RowModel):
    variant_id: str = Field(title="Variant")
    ref_snp_id: Optional[str] = Field(default=None, title="Ref SNP ID")

    # should allow to fill from SQLAlchemy ORM model
    model_config = ConfigDict(from_attributes=True)


class Variant(VariantFeature):
    variant_class: str = Field(title="Variant Type")
    location: GenomicRegion
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

    # FIXME: these queries can take a while; not part of the variant record
    # alternative_alleles: Optional[List[str]]
    # colocated_variants: Optional[List[Variant]]

    is_multi_allelic: bool = Field(
        default=False,
        title="Is Multi-allelic?",
        description="flag indicating whether the dbSNP refSNP is multi-allelic",
    )
    is_structural_variant: bool = Field(
        default=False,
        title="Is SV?",
        description="flag indicating whether the variant is a structural variant",
    )

    cadd_scores: Optional[CADDScore] = Field(
        serialization_alias="cadd_score",
        default=None,
        title="CADD Score(s)",
        description="score of the deleteriousness of a variant",
    )

    adsp_qc: Optional[List[QCStatus]] = None

    allele_frequencies: Optional[dict] = None
    ranked_consequences: Optional[RankedConsequences] = Field(
        default=None,
        title="VEP Ranked Consequences",
        description="ranked consequences from VEP analysis",
    )
    associations: Optional[dict] = Field(
        default=None,
        description="Significant assocaitions in NIAGADS GWAS summary statistics datasets",
    )

    # TODO: vrs: [VRS] - ga4gh variant representation
    @staticmethod
    def __boolean_null_check(v):
        if v is None:
            return False
        else:
            return v

    @field_validator("is_multi_allelic", mode="before")
    @classmethod
    def parse_is_multi_allelic(cls, v):
        return cls.__boolean_null_check(v)

    @field_validator("is_structural_variant", mode="before")
    @classmethod
    def parse_is_structural_variant(cls, v):
        return cls.__boolean_null_check(v)

    @field_validator("is_adsp_variant", mode="before")
    @classmethod
    def parse_is_adsp_variant(cls, v):
        return cls.__boolean_null_check(v)

    @field_validator("most_severe_consequence", mode="before")
    @classmethod
    def parse_most_severe_consequence(cls, v):
        if v is None or isinstance(v, PredictedConsequence):
            return v

        return PredictedConsequence.from_vep_json(v)

    @field_validator("adsp_qc", mode="before")
    @classmethod
    def parse_adsp_qc(cls, v):
        if v is None:
            return v
        if isinstance(v, QCStatus):
            return [QCStatus]
        if isinstance(v, list) and isinstance(v[0], QCStatus):
            return v
        if isinstance(v, dict):
            qc = []
            for release, scores in v.items():
                status = QCStatus(
                    status_code=scores["filter"],
                    passed="PASS" in scores["filter"],
                    release=release,
                    scores=scores["info"],
                )
                qc.append(status)
            return qc
        else:
            raise RuntimeError("Unexpected value returned for `adsp_qc` status")


class AbridgedVariantResponse(RecordResponse):
    data: List[Variant]


class VariantResponse(RecordResponse):
    data: List[AnnotatedVariant]
