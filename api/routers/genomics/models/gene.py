from typing import Dict, List, Optional, Union

from api.models.base_response_models import PagedResponseModel
from api.models.genome import Gene as BaseGene

class Gene(BaseGene):
    type: str
    name: str
    ids: Dict[str, Union[str, int]]
    cytogenic_location: Optional[str] = None
    summary: Optional[str] = None
    
class AnnotatedGene(Gene):
    rifs: Optional[dict] = None
    function: Optional[dict] = None
    pathways: Optional[dict] = None
    relationships: Optional[dict] = None
    
class GeneSummaryResponse(PagedResponseModel):
    response: List[Gene]
    
class AnnotatedGeneResponse(PagedResponseModel):
    response: List[AnnotatedGene]