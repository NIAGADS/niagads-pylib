from typing import List, Optional, Union
from niagads.database.schemas.dataset.composite_attributes import Phenotype
from niagads.database.schemas.variant.composite_attributes import (
    CADDScore,
    PredictedConsequence,
    QCStatus,
    RankedConsequences,
)

from niagads.genome.core import Human
from niagads.open_access_api_common.models.core import ORMCompatibleRowModel, RowModel
from niagads.open_access_api_common.models.features.genomic import GenomicRegion
from niagads.open_access_api_common.models.response.core import RecordResponse
from pydantic import (
    ConfigDict,
    Field,
    computed_field,
    field_validator,
)


class VariantFeature(ORMCompatibleRowModel):
    variant_id: str = Field(title="Variant")
    ref_snp_id: Optional[str] = Field(default=None, title="Ref SNP ID")


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


class SimpleAnnotatedVariant(Variant):
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

    def _flat_dump(self, nullFree=False, delimiter="|"):
        obj = super()._flat_dump(nullFree, delimiter=delimiter)

        # promote the location fields
        del obj["most_severe_consequence"]
        obj.update(self.most_severe_consequence._flat_dump())
        return obj

    @classmethod
    def get_model_fields(cls, asStr=False):
        fields = super().get_model_fields()

        del fields["most_severe_consequence"]
        fields.update(PredictedConsequence.get_model_fields())

        return list(fields.keys()) if asStr else fields


class AnnotatedVariant(SimpleAnnotatedVariant):

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


class VariantAssociation(ORMCompatibleRowModel):
    variant: Union[SimpleAnnotatedVariant] = Field(title="Variant")
    test_allele: str = Field(title="Test Allele")
    track_id: str = Field(title="Track")
    p_value: Union[float, str] = Field(title="p-Value")
    neg_log10_pvalue: float = Field(title="-log10pValue")
    subject_phenotypes: Optional[Phenotype] = Field(exclude=True)

    @computed_field
    @property
    def trait(self):
        pass  # implement as field_validator like w/abridgedtrack

    def _flat_dump(self, nullFree=False, delimiter="|"):
        obj = super()._flat_dump(nullFree, delimiter=delimiter)

        # promote the variant fields
        del obj["variant"]
        obj.update(self.variant._flat_dump())
        return obj

    @classmethod
    def get_model_fields(cls, asStr=False):
        fields = super().get_model_fields()

        del fields["subject_phenotypes"]
        del fields["variant"]
        fields.update(SimpleAnnotatedVariant.get_model_fields())

        return list(fields.keys()) if asStr else fields

    def table_fields(self, asStr=False, **kwargs):
        return super().table_fields(asStr, **kwargs)


class VariantAssociationResponse(RecordResponse):
    data: List[VariantAssociation]

    def to_vcf(self):
        raise NotImplementedError("VCF formatted responses coming soon.")

    def to_bed(self):
        raise NotImplementedError(
            "BED formatted responses not available for this type of data."
        )


class AbridgedVariantResponse(RecordResponse):
    data: List[Variant]


class VariantResponse(RecordResponse):
    data: List[AnnotatedVariant]
