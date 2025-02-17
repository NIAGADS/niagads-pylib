
from typing import List, Optional, Type, TypeVar, Union

from api.models.response_model_properties import RowModel
from api.models.base_response_models import PagedResponseModel
from api.models.genome import Gene, Variant

# TODO: NHGRI GWAS Catalog/ADVP data -> maybe just make VariantScore a `GenericDataModel`

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

class VariantScoreResponse(PagedResponseModel):
    response: List[Type[T_VariantScore]]
    
class xQTLResponse(PagedResponseModel):
    response: List[xQTL]
    
