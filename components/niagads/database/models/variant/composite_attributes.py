from enum import auto
from typing import List, Optional
from niagads.enums.core import CaseInsensitiveEnum
from pydantic import BaseModel, Field, computed_field


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


class PredictedConsequence(BaseModel):
    consequence: str
    impact: ConsequenceImpact
    is_coding: Optional[bool] = False
    impacted_gene_id: Optional[str] = Field(default=None, exclude=True)
    impacted_gene_symbol: Optional[str] = Field(default=None, exclude=True)
    impacted_gene: Optional[d] = Field(default=None, exlude=True)
    # info: Optional[dict] <- what else is there; depends on the type of consequence

    @computed_field(
        default=None,
        title="Impacted Gene",
        description="gene predicted to be impacted by the variant consequence",
    )
    @property
    def impacted_gene_symbol(self):
        # b/c a `GeneFeature` is a open_access_api response model
        if self.impacted_gene_id is not None:
            return {
                "id": self.impacted_gene_id,
                "gene_symbol": self.impacted_gene_symbol,
            }
        else:
            return None

    @staticmethod
    def get_impact_color(impact: str):
        return ConsequenceImpact(impact).color()


class RankedConsequences(BaseModel):
    regulatory: List[PredictedConsequence]
    motif: List[PredictedConsequence]
    transcript: List[PredictedConsequence]
