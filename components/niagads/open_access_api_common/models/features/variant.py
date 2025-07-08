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
from pydantic import Field, field_validator


class VariantFeature(RowModel):
    variant_id: str = Field(title="Variant", order=1)
    ref_snp_id: Optional[str] = Field(default=None, title="Ref SNP ID", order=1)


class Variant(VariantFeature):
    variant_class: str = Field(title="Variant Type")
    location: GenomicRegion
    ref: str
    alt: Optional[str] = None

    def _flat_dump(self, nullFree=False, delimiter="|"):
        obj = super()._flat_dump(nullFree, delimiter=delimiter)

        # promote the location fields
        del obj["location"]
        obj.update(self.location._flat_dump())
        return obj

    @classmethod
    def get_model_fields(cls, asStr=False):
        fields = super().get_model_fields()
        del fields["location"]
        fields.update(GenomicRegion.get_model_fields())

        return list(fields.keys()) if asStr else fields


class VariantDisplayAnnotation(RowModel):
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

    @field_validator("most_severe_consequence", mode="before")
    @classmethod
    def parse_most_severe_consequence(cls, v):
        if v is None:
            return None
        if not isinstance(v, dict):  # ORM response
            v = v.model_dump()
        try:
            conseq = PredictedConsequence(**v)
            return conseq
        except:
            return PredictedConsequence.from_vep_json(v)

    def _flat_dump(self, nullFree=False, delimiter="|"):
        obj = super()._flat_dump(nullFree, delimiter=delimiter)

        # promote the location fields
        del obj["most_severe_consequence"]
        if self.most_severe_consequence is not None:
            obj.update(self.most_severe_consequence._flat_dump())
        else:
            obj.update(
                {k: None for k in PredictedConsequence.get_model_fields(asStr=True)}
            )
        return obj

    @classmethod
    def get_model_fields(cls, asStr=False):
        fields = super().get_model_fields()

        del fields["most_severe_consequence"]
        fields.update(PredictedConsequence.get_model_fields())

        return list(fields.keys()) if asStr else fields


class AnnotatedVariant(VariantFeature, VariantDisplayAnnotation):
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
