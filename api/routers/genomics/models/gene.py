from typing import Dict, List, Optional, Union

from api.models.base_response_models import PagedResponseModel
from api.models.genome import Gene as BaseGene

class Gene(BaseGene):
    type: str
    name: str
    ids: Dict[str, Union[str, int]]
    cytogenic_location: Optional[str]
    summary: Optional[str]
    
class AnnotatedGene(Gene):
    rifs: Optional[dict]
    function: Optional[dict]
    pathways: Optional[dict]
    relationships: Optional[dict]
    
class GeneSummaryResponse(PagedResponseModel):
    response: List[Gene]
    
class AnnotatedGeneResponse(PagedResponseModel):
    response: List[AnnotatedGene]