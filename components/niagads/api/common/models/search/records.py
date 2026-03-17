from typing import List, Self

from niagads.api.common.models.base import (
    ORMCompatibleDynamicRowModel,
    ORMCompatibleRowModel,
)
from niagads.api.common.models.records import Entity
from niagads.api.common.models.response.record import RecordResponse
from pydantic import Field


class ResultSize(ORMCompatibleDynamicRowModel):
    num_results: int = Field(
        title="Num. Results",
        description="number of search results",
    )

    def __str__(self):
        return self.as_info_string()

    @staticmethod
    def sort(results: List[Self], reverse=True) -> List[Self]:
        """sorts a list of track results"""
        return sorted(results, key=lambda item: item.num_results, reverse=reverse)


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
