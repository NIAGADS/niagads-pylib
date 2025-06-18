from typing import List

from niagads.open_access_api_common.models.core import Entity
from niagads.open_access_api_common.models.records.core import RowModel
from niagads.open_access_api_common.models.response.core import GenericResponse
from pydantic import AliasChoices, Field


class RecordSearchResult(RowModel):
    id: str = Field(
        validation_alias=AliasChoices("primary_key")
    )  # primary_key (identifier) for the record (e.g., ensembl ID)
    description: str  # descriptive text
    display: str  # display id (e.g. gene symbol)
    record_type: Entity
    matched_term: str
    match_rank: int


class RecordSearchResultResponse(GenericResponse):
    data: List[RecordSearchResult]
