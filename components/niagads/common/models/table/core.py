"""Table View Data and Response Models

FIXME: remove front end rendering and place in configuration JSON
"""

from typing import Dict, List, Optional
from niagads.common.models.table.cells import TableCell, TableCellType
from pydantic import BaseModel, ConfigDict, model_validator


class TableRow(BaseModel):
    __pydantic_extra__: Dict[str, TableCell]
    model_config = ConfigDict(extra="allow")


# FIXME: get columns and options from config files
class TableColumn(BaseModel):
    header: Optional[str] = None
    id: str
    description: Optional[str] = None
    type: Optional[TableCellType] = TableCellType.ABSTRACT
    canFilter: bool = True
    disableGlobalFilter: bool = False
    disableSorting: bool = False
    required: Optional[bool] = False

    @model_validator(mode="after")
    def validate_options(self):
        if self.type in [
            TableCellType.INTEGER,
            TableCellType.FLOAT,
            TableCellType.PVALUE,
        ]:
            self.disableGlobalFilter = True


class Table(BaseModel):
    data: List[TableRow]
    columns: List[TableColumn]
