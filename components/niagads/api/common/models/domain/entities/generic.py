from niagads.api.common.data_models.mixins import ORMCompatabileMixin
from niagads.enums.core import CaseInsensitiveEnum
from pydantic import BaseModel, Field


class Entity(CaseInsensitiveEnum):
    GENE = "gene"
    VARIANT = "variant"
    SPAN = "span"
    TRACK = "track"
    COLLECTION = "collection"

    def __str__(self):
        return self.value.title()


class EntityRecordStats(BaseModel):
    entity: Entity
    num_records: int


class EntityRecordMatch(ORMCompatabileMixin):
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
