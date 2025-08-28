from typing import List, Optional, Union

from fastapi import HTTPException
from niagads.common.models.core import TransformableModel
from niagads.api_common.views.table import TableRow
from niagads.api_common.models.features.genomic import GenomicRegion
from niagads.common.models.composite_attributes.variant import (
    CADDScore,
    PredictedConsequenceSummary,
    QCStatus,
)

from niagads.api_common.models.core import RowModel
from niagads.api_common.models.response.core import RecordResponse
from pydantic import Field, field_validator


class VariantFeature(RowModel):
    variant_id: str = Field(title="Variant", order=1, serialization_alias="id")
    ref_snp_id: Optional[str] = Field(default=None, title="Ref SNP ID", order=1)


class AbridgedVariant(VariantFeature):
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

    def _flat_dump(self, nullFree=False, delimiter="|"):
        obj = super()._flat_dump(nullFree, delimiter=delimiter)

        # promote the location fields
        del obj["most_severe_consequence"]
        if self.most_severe_consequence is not None:
            obj.update(self.most_severe_consequence._flat_dump())
        else:
            obj.update(
                {
                    k: None
                    for k in PredictedConsequenceSummary.get_model_fields(as_str=True)
                }
            )

        return obj

    @classmethod
    def get_model_fields(cls, as_str=False):
        fields = super().get_model_fields()

        del fields["most_severe_consequence"]
        fields.update(PredictedConsequenceSummary.get_model_fields())

        return list(fields.keys()) if as_str else fields

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


class Variant(AbridgedVariant):

    location: GenomicRegion
    ref: Optional[str] = Field(default=None, title="Reference Allele")
    alt: Optional[str] = Field(default=None, title="Alternative Allele")
    allele_string: Optional[str] = Field(default=None, title="Allele String")

    is_structural_variant: bool = Field(
        default=False,
        title="Is SV?",
        description="flag indicating whether the variant is a structural variant",
    )

    def _flat_dump(self, nullFree=False, delimiter="|"):
        obj = super()._flat_dump(nullFree, delimiter=delimiter)

        # promote the location fields
        del obj["location"]
        obj.update(self.location._flat_dump())

        return obj

    @classmethod
    def get_model_fields(cls, as_str=False):
        fields = super().get_model_fields()

        del fields["location"]
        fields.update(GenomicRegion.get_model_fields())

        return list(fields.keys()) if as_str else fields

    @field_validator("is_structural_variant", mode="before")
    @classmethod
    def parse_is_structural_variant(cls, v):
        return cls.boolean_null_check(v)


class AnnotatedVariant(Variant):

    # FIXME: these queries can take a while; not part of the variant record
    # alternative_alleles: Optional[List[str]]
    # colocated_variants: Optional[List[Variant]]

    is_multi_allelic: bool = Field(
        default=False,
        title="Is Multi-allelic?",
        description="flag indicating whether the dbSNP refSNP is multi-allelic",
    )

    cadd_scores: Optional[CADDScore] = Field(
        serialization_alias="cadd_score",
        default=None,
        title="CADD Score(s)",
        description="score of the deleteriousness of a variant",
    )

    adsp_qc: Optional[List[QCStatus]] = None

    allele_frequencies: Optional[dict] = Field(
        default=None, description="allele frequencies from 1000Genomes, ALFA, ExAC"
    )
    ranked_consequences: Optional[dict] = Field(
        default=None,
        serialization_alias="predicted_consequences",
        description="all predicted consequences from VEP annotation",
    )

    # TODO: vrs: [VRS] - ga4gh variant representation

    @field_validator("is_multi_allelic", mode="before")
    @classmethod
    def parse_is_multi_allelic(cls, v):
        return cls.boolean_null_check(v)

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


class FrequencyPopulation(TransformableModel):
    abbreviation: str = Field(title="Population")
    population: str = Field(title="Population")
    description: Optional[str] = None

    def __str__(self):
        return self.population


class AlleleFrequencies(RowModel):
    population: FrequencyPopulation = Field(title="Population", order=1)
    allele: str = Field(title="Allele", order=3)

    data_source: str = Field(
        title="Resource",
        description="original data source for the frequency information",
        order=2,
    )
    frequency: str = Field(title="Frequency", order=4)

    def as_table_row(self, **kwargs):
        row = self._flat_dump(delimiter=" // ")
        population = {"value": self.population.population}
        if self.population.description is not None:
            population.update({"info": self.population.description})
        row.update({"population": population})
        return TableRow(**row)


class VariantFunction(RowModel):
    """ranked consequences"""

    pass


class ColocatedVariants(RowModel):
    alternative_alleles: Optional[List[str]] = None
    colocated_variants: Optional[List[str]] = None

    def as_table_row(self, **kwargs):
        raise NotImplementedError(
            "Table views not available for lists of co-located variants."
        )

    def as_text(self, fields=None, null_str="NA", **kwargs):
        raise NotImplementedError(
            "Plain text response not available for lists of co-located variants."
        )


class VariantAnnotationResponse(RecordResponse):
    data: Union[
        List[ColocatedVariants],
        List[VariantFunction],
        List[AlleleFrequencies],
        List[RowModel],
    ]


class AbridgedVariantResponse(RecordResponse):
    data: List[Variant]


class VariantResponse(RecordResponse):
    data: List[AnnotatedVariant]

    def to_text(self, incl_header=False, null_str=""):
        raise NotImplementedError(
            "TEXT formatted output not available for a FULL variant response; set `content=brief` to get a plain text table."
        )
