from typing import List, Optional, Set

from niagads.common.types import T_PubMedID
from niagads.api.common.models.core import RowModel
from niagads.api.common.models.records import RecordSummary


class RouteDescription(RowModel):
    name: str
    description: str
    publications: Optional[Set[T_PubMedID]] = None
    url: str
    records: List[RecordSummary]
