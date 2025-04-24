from typing import List, Optional, Set
from niagads.open_access_api_common.models.records.core import RowModel
from niagads.open_access_api_common.types import RecordType, T_PubMedID
from pydantic import BaseModel, Field


class RecordSummary(BaseModel):
    record_type: RecordType
    num_records: int


class RouteDescription(RowModel):
    name: str
    description: str
    publications: Optional[Set[T_PubMedID]] = None
    url: str
    records: List[RecordSummary]
