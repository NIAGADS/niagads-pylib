from niagads.api.common.models.domain.base import ORMCompatibleRecord
from niagads.common.types import Entity
from niagads.enums.core import CaseInsensitiveEnum
from pydantic import BaseModel, Field


class EntityMetrics(BaseModel):
    entity: Entity
    num_records: int


class EntityRecordMatch(ORMCompatibleRecord):
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
