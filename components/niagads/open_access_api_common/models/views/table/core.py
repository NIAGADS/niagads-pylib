"""Table View Data and Response Models

FIXME: remove front end rendering and place in configuration JSON
"""

from typing import Optional


from niagads.common.models.table.core import Table
from niagads.open_access_api_common.models.views.core import ViewResponse


class TableViewModel(Table):
    id: str
    title: Optional[str]


class TableViewResponse(ViewResponse):
    table: TableViewModel
