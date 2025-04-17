from enum import StrEnum, auto
from typing import Any, Dict, List, Optional, TypeVar, Union

from niagads.open_access_api_base_models.core import NullFreeModel

# FIXME: is front-end; can we refactor?

class TableCellType(StrEnum):
    BOOLEAN = auto()
    ABSTRACT = auto()
    FLOAT = auto()
    PVALUE = "p_value"
    TEXT = auto()
    TEXT_LIST = auto()
    BADGE = auto()
    LINK = auto()
    LINK_LIST = auto()
    PERCENTAGE = "percentage_bar"
    
    def __str__(self):
        return self.value.lower()

class BadgeIcon(StrEnum):
    CHECK = 'check'
    SOLID_CHECK = 'solidCheck'
    INFO = 'info'
    WARNING = 'warning'
    USER = 'user'
    INFO_OUTLINE = 'infoOutline'
    X_MARK = 'xMark'    
    
    
    def __str__(self):
        return self.value

    
class TableCell(NullFreeModel):
    type: TableCellType = TableCellType.ABSTRACT
    value: Optional[Union[str, bool, int, float]] = None
    # nullValue: Optional[str] = None
    # naValue: Optional[str] = 'NA'

class FloatTableCell(TableCell):
    type:TableCellType = TableCellType.FLOAT
    value: Optional[Union[int, float]] = None
    precision: Optional[int] = 2
    
class PValueTableCell(FloatTableCell):
    type: TableCellType = TableCellType.PVALUE
    value:Optional[float] = None
    neg_log10_pvalue: Optional[float] = None

class TextTableCell(TableCell):
    type: TableCellType = TableCellType.TEXT
    value:Optional[str] = None
    truncateTo:Optional[int] = 100
    color: Optional[str] = None
    tooltip: Optional[str] = None

class TextListTableCell(TableCell):
    type: TableCellType = TableCellType.TEXT_LIST
    value:Optional[str] = None
    items: Optional[List[TextTableCell]]

class BadgeTableCell(TextTableCell):
    type: TableCellType = TableCellType.BADGE
    backgroundColor:Optional[str] = None
    borderColor: Optional[str] = None
    icon: Optional[BadgeIcon] = None

class BooleanTableCell(BadgeTableCell):
    type: TableCellType = TableCellType.BOOLEAN
    value:Optional[bool] = None
    displayText: Optional[Union[str, bool]] = None
    
class LinkTableCell(TableCell):
    type: TableCellType = TableCellType.LINK
    url:Optional[str] = None
    tooltip: Optional[str] = None
    
class LinkListTableCell(TableCell):
    type: TableCellType = TableCellType.LINK_LIST
    value:Optional[str] = None
    items:Optional[List[LinkTableCell]]
    

class PercentagBarTableCell(FloatTableCell):
    type: TableCellType = TableCellType.PERCENTAGE
    colors: Optional[List[str]] = None


T_TableCell = TypeVar('T_TableCell', bound=TableCell)

# FIXME: validation failing to recognize subclasses of T_TableCell; see notes in genomics_tracks.py
T_TableRow = Dict[str, Any] # Dict[str, Union[Type[T_TableCell], int, float, str, bool, None]]