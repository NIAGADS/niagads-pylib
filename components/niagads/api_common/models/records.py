from niagads.enums.core import CaseInsensitiveEnum
from pydantic import BaseModel


class Entity(CaseInsensitiveEnum):
    GENE = "gene"
    VARIANT = "variant"
    SPAN = "span"
    TRACK = "track"

    def __str__(self):
        return self.value.title()


class RecordSummary(BaseModel):
    entity: Entity
    num_records: int
