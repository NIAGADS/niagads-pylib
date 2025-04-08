from typing import Dict, List, Optional, Union

from api.models.base_response_models import PagedResponseModel
from api.models.genome import Gene as BaseGene, GenomicRegion

class Gene(BaseGene):
    type: str
    name: str
    location: GenomicRegion
    cytogenic_location: Optional[str] = None
    # summary: Optional[str] = None

class AnnotatedGene(Gene):
    mappings: Dict[str, Union[str, int]]
    # rifs: Optional[dict] = None
    function: Optional[dict] = None
    pathways: Optional[dict] = None
    # relationships: Optional[dict] = None
    
class GeneSummaryResponse(PagedResponseModel):
    data: List[Gene]
    
class AnnotatedGeneResponse(PagedResponseModel):
    data: List[AnnotatedGene]