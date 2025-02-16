from typing import Any, Dict, List, Optional, Union
from pydantic import ConfigDict

from api.common.enums import ConsequenceImpact
from api.models.base_models import RowModel, SerializableModel
from api.models.base_response_models import PagedResponseModel
from api.models.genome import Gene, Variant as BaseVariant

class PredictedConsequence(RowModel):
    consequence: str
    impact: ConsequenceImpact
    is_coding: Optional[bool]
    impacted_gene: Optional[Gene]
    # info: Optional[dict] <- what else is there; depends on the type of consequence

class Variant(BaseVariant):
    type: str
    is_adsp_variant: bool
    most_serious_consequence: PredictedConsequence
    cadd_score: Dict[str, float]
    # is_multi_allelic: bool

class AnnotatedVariant(Variant):
    ADSP_qc: Optional[Dict[str, Union[str, int, bool]]]
    allele_frequencies: Optional[dict]
    predicted_consequences: Optional[Dict[str, PredictedConsequence]]
    # predicted consequences
    # lof
    # favor annotations
    # ld -> maybe?
    

    # FIXME: not sure on this
    # model_config = ConfigDict(exclude_none=True)


class VariantSummaryResponse(PagedResponseModel):
    response: List[Variant]
    
class AnnotatedVariantResponse(PagedResponseModel):
    response: List[AnnotatedVariant]