
from typing import List, Optional, Type, TypeVar, Union

from api.models.base_models import RowModel
from api.models.base_response_models import PagedResponseModel
from api.models.genome import Gene, Variant



class VariantScore(RowModel):
    variant: Variant
    test_allele: str
    track_id: str

T_VariantScore = TypeVar('T_SerializableModel', bound=VariantScore)

class VariantPValueScore(VariantScore):
    p_value: Union[float, str]
    neg_log10_pvalue: float
    
class xQTL(VariantPValueScore):
    z_score: Optional[float]
    dist_to_target: Optional[float]
    target: Gene
    pass


class VariantScoreResponse(PagedResponseModel):
    response: List[Type[T_VariantScore]]
    
class xQTLResponse(PagedResponseModel):
    response: List[xQTL]
    
