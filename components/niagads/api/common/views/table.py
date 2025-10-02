from typing import Optional, Union

from niagads.common.models.views.table import BaseTable
from niagads.api.common.views.core import ViewResponse


class Table(BaseTable):
    id: str
    title: Optional[str] = None


class TableViewResponse(ViewResponse):
    table: Union[Table, dict]
