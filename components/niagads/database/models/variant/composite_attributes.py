from enum import auto
from typing import List, Optional
from niagads.enums.core import CaseInsensitiveEnum
from niagads.open_access_api_common.models.records.features.gene import GeneFeature
from pydantic import BaseModel


class ConsequenceImpact(CaseInsensitiveEnum):
    HIGH = auto()
    MODERATE = auto()
    LOW = auto()
    MODIFIER = auto()


class PredictedConsequence(BaseModel):
    consequence: str
    impact: ConsequenceImpact
    is_coding: Optional[bool] = False
    impacted_gene: Optional[GeneFeature] = None
    # info: Optional[dict] <- what else is there; depends on the type of consequence

    @staticmethod
    def get_impact_color(impact: str):
        match impact:
            case "HIGH" | "high":
                return "#ff00ff"
            case "MODERATE" | "moderate":
                return "#f59300"
            case "MODIFIER" | "modifier":
                return "#377eb8"
            case "LOW" | "low":
                return "#377eb8"
            case _:
                return None


class RankedConsequences(BaseModel):
    regulatory: List[PredictedConsequence]
    motif: List[PredictedConsequence]
    transcript: List[PredictedConsequence]
