from typing import Any, Dict, List, Optional, Union

from pydantic import ConfigDict
from api.models.base_response_models import PagedResponseModel
from api.models.genome import Variant

class AnnotatedVariantSummary(Variant):
    type: str
    is_adsp_variant: bool
    most_serious_consequence: dict
    cadd_score: Dict[str, float]
    is_multi_allelic: bool

class AnnotatedVariant(AnnotatedVariantSummary):
    ADSP_qc: Optional[Dict[str, Union[str, int, bool]]]
    allele_frequencies: Optional[dict]
    # predicted consequences
    # lof
    # favor annotations
    # ld -> maybe?
    

    # FIXME: not sure on this
    # model_config = ConfigDict(exclude_none=True)


class AnnotatedVariantSummaryResponse(PagedResponseModel):
    response: List[AnnotatedVariantSummary]
    
class AnnotatedVariantResponse(PagedResponseModel):
    response: List[AnnotatedVariant]