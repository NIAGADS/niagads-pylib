from typing import Any, Dict, List, Optional, Union
from pydantic import BaseModel, ConfigDict


from api.models.base_response_models import PagedResponseModel
from api.models.base_row_models import RowModel

from api.models.genome import Gene, GenomicRegion, Variant as BaseVariant
from api.routes.genomics.common.enums import ConsequenceImpact

class PredictedConsequence(BaseModel):
    consequence: str
    impact: ConsequenceImpact
    is_coding: Optional[bool] = False
    impacted_gene: Optional[Gene] = None
    # info: Optional[dict] <- what else is there; depends on the type of consequence
    
    @staticmethod
    def get_impact_color(impact:str):
        match impact:
            case 'HIGH' | 'high':
                return "#ff00ff"
            case 'MODERATE' | 'moderate':
                return "#f59300"
            case 'MODIFIER' | 'modifier':
                return "#377eb8"
            case 'LOW' | 'low':
                return "#377eb8"
            case _:
                return None

class RankedConsequences(BaseModel):
    regulatory: List[PredictedConsequence]
    motif: List[PredictedConsequence]
    transcript: List[PredictedConsequence]

class Variant(BaseVariant):
    type: str
    is_adsp_variant: Optional[bool] = False
    most_severe_consequence: Optional[PredictedConsequence] = None
    # is_multi_allelic: bool

class AnnotatedVariant(Variant):
    length: str # or location: GenomicRegion?
    cadd_score: Optional[Dict[str, float]] = None
    ADSP_qc: Optional[Dict[str, dict]] = None
    allele_frequencies: Optional[dict] = None
    predicted_consequences: Optional[RankedConsequences] = None
    # predicted consequences
    # lof
    # favor annotations
    # ld -> maybe?
    


class VariantSummaryResponse(PagedResponseModel):
    response: List[Variant]
    
class AnnotatedVariantResponse(PagedResponseModel):
    response: List[AnnotatedVariant]