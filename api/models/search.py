from enum import auto
from typing import List

from pydantic import AliasChoices, Field

from api.common.enums.base_enums import CaseInsensitiveEnum
from api.models.base_row_models import RowModel

from .base_response_models import PagedResponseModel

# TODO: leave here for now b/c not sure if required
# if required, value probably needs to be endpoint;
# so maybe need to override __str__
class RecordType(CaseInsensitiveEnum):
    TRACK = 'track'
    GENE = 'gene'
    VARIANT = 'variant'
    COLLECTION = 'collection'

class RecordSearchResult(RowModel):
    id: str = Field(validation_alias=AliasChoices('primary_key')) # primary_key (identifier) for the record (e.g., ensembl ID)
    description: str # descriptive text
    display: str # display id (e.g. gene symbol)
    record_type: RecordType
    matched_term: str
    match_rank: int
    
    
class RecordSearchResultResponse(PagedResponseModel):
    response: List[RecordSearchResult]