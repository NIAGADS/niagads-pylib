from niagads.common.models.base import CustomBaseModel
from niagads.common.types import Entity


class RecordSummary(CustomBaseModel):
    entity: Entity
    num_records: int
