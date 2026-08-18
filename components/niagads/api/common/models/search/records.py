from niagads.api.common.models.records.base import ORMCompatibleRecord
from niagads.api.common.types import Entity
from pydantic import Field


class SearchResult(ORMCompatibleRecord):
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
