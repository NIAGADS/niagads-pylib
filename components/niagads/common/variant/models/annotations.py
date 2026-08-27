from typing import List, Optional

from niagads.common.gene.models.record import GeneIdentifier
from niagads.common.models.base import CustomBaseModel
from niagads.common.variant.models.record import VariantIdentifier
from niagads.common.variant.types import ConsequenceImpact
from pydantic import BaseModel, Field


class FrequencyPopulation(CustomBaseModel):
    abbreviation: str = Field(title="Population")
    population: str = Field(title="Population")
    description: Optional[str] = None

    def __str__(self):
        return self.population


class AlleleFrequencies(CustomBaseModel):
    population: FrequencyPopulation = Field(title="Population", order=1)
    allele: str = Field(title="Allele", order=3)

    data_source: str = Field(
        title="Resource",
        description="original data source for the frequency information",
        order=2,
    )
    frequency: str = Field(title="Frequency", order=4)


class LDPartner(VariantIdentifier):
    """Represents a variant in linkage disequilibrium (LD) with another variant.

    Inherits from VariantIdentifier:
        ref_snp_id (Optional[str]): Reference SNP ID (e.g., rsID).
        positional_id (str): Positional variant identifier.

    Additional LD attributes:
        r_squared (float): Squared correlation coefficient (r²) between variants.
        r (float): Correlation coefficient between variants.
        d (float): D statistic for LD.
        d_prime (float): D' statistic for LD.
    """

    r_squared: float
    r: float
    d: float
    d_prime: float


class PredictedConsequenceSummary(CustomBaseModel):
    consequence_terms: List[str] = Field(title="Predicted Consequence(s)")
    impact: ConsequenceImpact = Field(title="Impact")
    is_coding: Optional[bool] = Field(
        default=False, serialization_alias="is_coding", title="Is Coding?"
    )
    impacted_gene: Optional[GeneIdentifier] = Field(default=None, title="Impacted Gene")
    impacted_transcript: Optional[str] = Field(
        default=None, title="Impacted Transcript"
    )
    codon_change: Optional[str] = Field(default=None, title="Codon Change")
    amino_acid_change: Optional[str] = Field(default=None, title="Amino Acid Change")

    @staticmethod
    def get_impact_color(impact: str):
        return ConsequenceImpact(impact).color()

    @classmethod
    def from_vep_json(cls, v: dict):
        impactedGene = v.get("gene_id")
        if impactedGene is not None:
            impactedGene = {"id": v["gene_id"], "gene_symbol": v.get("gene_symbol")}

        return cls(
            consequence_terms=v["consequence_terms"],
            impact=ConsequenceImpact(v["impact"]),
            is_coding=v.get("consequence_is_coding", False),
            impacted_gene=(
                GeneIdentifier(**impactedGene) if impactedGene is not None else None
            ),
            impacted_transcript=v.get("transcript_id"),
            codon_change=v.get("codons"),
            amino_acid_chnge=v.get("amino_acids"),
        )


class RankedPredictedConsequence(PredictedConsequenceSummary):
    pass


class RannkedTranscriptConsequences(RankedPredictedConsequence):
    pass


class RankedConsequences(BaseModel):
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
