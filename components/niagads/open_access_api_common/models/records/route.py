from typing import List, Optional, Set

from niagads.common.types.core import T_PubMedID
from niagads.open_access_api_common.models.records.core import RowModel
from niagads.open_access_api_common.types import Entity
from pydantic import BaseModel


class RecordSummary(BaseModel):
    record_type: Entity
    num_records: int


class RouteDescription(RowModel):
    name: str
    description: str
    publications: Optional[Set[T_PubMedID]] = None
    url: str
    records: List[RecordSummary]
