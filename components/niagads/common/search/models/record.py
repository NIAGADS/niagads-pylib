from typing import Optional

from niagads.api.common.models.records import Entity
from niagads.common.models.base import CustomBaseModel
from niagads.common.search.types import MatchType
from pydantic import Field


class RecordSummary(CustomBaseModel):
    id: str
    name: str
    description: Optional[str] = None


class SearchResultRecord(CustomBaseModel):
    record_id: str = Field(
        serialization_alias="id",
        title="Record ID",
        description="unique record identifier",
    )
    # FIXME: define record summary for each record type -> display_id, description?
    record_summary: RecordSummary = Field(
        title="Basic identifying informatin for the record"
    )
    record_type: Entity = Field(title="Record Type")
    matched_text: str = Field(title="Matched", description="matched term or phrase")
    match_type: MatchType = Field(
        title="Match Type", description=f"type of match, one of {MatchType.list()}"
    )
    rank: int = Field(
        title="Match Rank",
        description="ranked confidence in rank (0 - exact, with decreasing confidence as rank increases) "
        "based on match type and semantic similarity score (when relevant).  "
        "Exact matches are always ranked the highest, but other rankings will depend on search strategy.",
    )
    score: Optional[float] = Field(
        default=None, title="Score", description="semantic similarity, if relevant"
    )
