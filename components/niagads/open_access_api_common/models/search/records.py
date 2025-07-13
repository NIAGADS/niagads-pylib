from typing import List

from niagads.open_access_api_common.constants import DEFAULT_NULL_STRING
from niagads.open_access_api_common.models.core import ORMCompatibleRowModel
from niagads.open_access_api_common.models.records import Entity
from niagads.open_access_api_common.models.response.core import RecordResponse
from pydantic import Field


class RecordSearchResult(ORMCompatibleRowModel):
    primary_key: str = Field(
        serialization_alias="id",
        title="Record ID",
        description="unique record identifier",
    )
    description: str  # descriptive text
    display: str = Field(title="Display ID")  # display id (e.g. gene symbol)
    record_type: Entity = Field(title="Record Type")
    matched_term: str = Field(title="Matched", description="matched term or phrase")
    match_rank: int


class RecordSearchResultResponse(RecordResponse):
    data: List[RecordSearchResult]

    def to_text(self, incl_header=False, null_str="NA"):
        raise NotImplementedError(
            "TEXT formatted output not available for a search result response."
        )
