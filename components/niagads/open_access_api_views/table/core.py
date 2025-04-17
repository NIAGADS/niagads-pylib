"""Table View Data and Response Models

FIXME: remove front end rendering and place in configuration JSON 
"""

from typing import Any, Dict, List, Optional

from niagads.open_access_api_base_models.core import NullFreeModel
from niagads.open_access_api_base_models.views import BaseViewResponseModel
from niagads.open_access_api_views.table.cells import T_TableRow, TableCellType
from pydantic import BaseModel

# FIXME: get columns and options from config files
class TableColumn(NullFreeModel):
    header: Optional[str] = None
    id: str
    description: Optional[str] = None
    type: Optional[TableCellType] = TableCellType.ABSTRACT
    canFilter: Optional[bool] = None
    disableGlobalFilter: Optional[bool] = None
    disableSorting: Optional[bool] = None
    required: Optional[bool] = None


class TableViewModel(BaseModel, arbitrary_types_allowed=True):
    data: List[T_TableRow]
    columns: List[TableColumn]
    options: Optional[Dict[str, Any]] = None
    id: str
    
class TableViewResponse(BaseViewResponseModel):
    table: TableViewModel
    
