from enum import auto
from typing import List, Optional
from niagads.database.models.core import CompositeAttributeModel
from niagads.enums.core import CaseInsensitiveEnum
from pydantic import ConfigDict, Field, computed_field, field_validator, model_validator


class ConsequenceImpact(CaseInsensitiveEnum):
    HIGH = auto()
    MODERATE = auto()
    LOW = auto()
    MODIFIER = auto()

    @classmethod
    def color(self):
        match self.name:
            case "HIGH" | "high":
                return "#ff00ff"
            case "MODERATE" | "moderate":
                return "#f59300"
            case "MODIFIER" | "modifier":
                return "#377eb8"
            case "LOW" | "low":
                return "#377eb8"
            case _:
                raise ValueError(f"Invalid consequence impact: {str(self)}")


class QCStatus(CompositeAttributeModel):
    status_code: str = Field(
        title="QC Status Code",
        description="specific QC status indicator; may vary with ADSP release",
    )  #  b/c there are some arbitrary codes
    passed: bool = Field(
        title="QC Status",
        description="flag indicating whether the variant passed QC",
    )
    release: str = Field(title="ADSP Release")
    scores: dict = Field(
        title="QC Scores",
        description="scores and annotations related to the QC testing",
    )

    # TODO: bring these in after can annotate title/description
    # add to info?
    # qual: int
    # format: Optional[str]


class CADDScore(CompositeAttributeModel):
    CADD_phred: float = Field(
        serialization_alias="phred",
        alias_priority=2,
        title="CADD PHRED-scaled Score",
        description=(
            "Normalized score representing rank of variant in genome-wide distribution; "
            "higher value suggests variant is more likely to be functionally significant. "
            "For SNVs, score of 20 or higher is in the top 1% of all potential causal variants"
        ),
    )
    CADD_raw_score: float = Field(
        serialization_alias="raw",
        title="CADD Raw Score",
        description="initial, unscaled output from the CADD model; not directly comparable across experiments",
    )


class PredictedConsequence(CompositeAttributeModel):
    consequence: List[str]
    impact: ConsequenceImpact
    is_coding: Optional[bool] = Field(default=False, serialization_alias="is_coding")
    impacted_gene: Optional[dict] = Field(default=None, exlude=True)
    impacted_transcript: Optional[str]
    codon_change: Optional[str] = None
    amino_acid_change: Optional[str] = None

    @staticmethod
    def get_impact_color(impact: str):
        return ConsequenceImpact(impact).color()

    @classmethod
    def from_vep_json(cls, v: dict):
        impactedGene = v.get("gene_id")
        if impactedGene is not None:
            impactedGene = {"id": v["gene_id"], "gene_symbol": v.get("gene_symbol")}

        return cls(
            consequence=v["consequence_terms"],
            impact=ConsequenceImpact(v["impact"]),
            is_coding=v.get("consequence_is_coding", False),
            impacted_gene=impactedGene,
            impacted_transcript=v.get("transcript_id"),
            codon_change=v.get("codons"),
            amino_acid_chnge=v.get("amino_acids"),
        )


class RankedConsequences(CompositeAttributeModel):
    transcript_consequences: List[dict] = Field(
        default=None, serialization_alias="transcript"
    )
    regulatory_consequences: List[dict] = Field(
        default=None, serialization_alias="regulatory"
    )
    motif_consequences: List[dict] = Field(default=None, serialization_alias="motif")
    intergenic_consequences: List[dict] = Field(
        default=None, serialization_alias="intergenic"
    )
