from typing import Optional

from niagads.common.models.views.table import BaseTable
from niagads.open_access_api_common.views.core import ViewResponse


class Table(BaseTable):
    id: str
    title: Optional[str] = None


class TableViewResponse(ViewResponse):
    table: Table
