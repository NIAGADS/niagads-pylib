from typing import Dict, List, Optional, Union

from api.models.base_response_models import PagedResponseModel
from api.models.genome import Gene

class AnnotatedGeneSummary(Gene):
    type: str
    name: str
    ids: Dict[str, Union[str, int]]
    cytogenic_location: Optional[str]
    summary: Optional[str]
    
class AnnotatedGene(AnnotatedGeneSummary):
    function: Optional[dict]
    pathways: Optional[dict]
    relationships: Optional[dict]
    
class AnnotatedGeneSummaryResponse(PagedResponseModel):
    response: List[AnnotatedGeneSummary]
    
class AnnotatedGeneResponse(PagedResponseModel):
    response: List[AnnotatedGene]