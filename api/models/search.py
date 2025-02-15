from typing import List
from pydantic import BaseModel

from api.common.enums import RecordType

from .base_response_models import PagedResponseModel

class RecordSearchResult(BaseModel):
    id: str # primary_key (identifier) for the record (e.g., ensembl ID)
    description: str # descriptive text
    display: str # display id (e.g. gene symbol)
    type: RecordType # one of gene, variant, track, collection, etc
    matched_term: str
    match_rank: int
    
    
class RecordSearchResultResposne(PagedResponseModel):
    response: List[RecordSearchResult]