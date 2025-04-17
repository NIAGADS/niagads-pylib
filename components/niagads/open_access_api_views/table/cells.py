from enum import StrEnum, auto
from typing import Any, Dict, List, Optional, TypeVar, Union

from niagads.open_access_api_base_models.core import NullFreeModel

# FIXME: is front-end; can we refactor?

class CellType(StrEnum):
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

    
class DataCell(NullFreeModel):
    type: CellType = CellType.ABSTRACT
    value: Optional[Union[str, bool, int, float]] = None
    # nullValue: Optional[str] = None
    # naValue: Optional[str] = 'NA'


T_DataCell = TypeVar('T_DataCell', bound=DataCell)

class FloatDataCell(DataCell):
    type:CellType = CellType.FLOAT
    value: Optional[Union[int, float]] = None
    precision: Optional[int] = 2
    
class PValueDataCell(FloatDataCell):
    type: CellType = CellType.PVALUE
    value:Optional[float] = None
    neg_log10_pvalue: Optional[float] = None

class TextDataCell(DataCell):
    type: CellType = CellType.TEXT
    value:Optional[str] = None
    truncateTo:Optional[int] = 100
    color: Optional[str] = None
    tooltip: Optional[str] = None

class TextListDataCell(DataCell):
    type: CellType = CellType.TEXT_LIST
    value:Optional[str] = None
    items: Optional[List[TextDataCell]]

class BadgeDataCell(TextDataCell):
    type: CellType = CellType.BADGE
    backgroundColor:Optional[str] = None
    borderColor: Optional[str] = None
    icon: Optional[BadgeIcon] = None

class BooleanDataCell(BadgeDataCell):
    type: CellType = CellType.BOOLEAN
    value:Optional[bool] = None
    displayText: Optional[Union[str, bool]] = None
    
class LinkDataCell(DataCell):
    type: CellType = CellType.LINK
    url:Optional[str] = None
    tooltip: Optional[str] = None
    
class LinkListDataCell(DataCell):
    type: CellType = CellType.LINK_LIST
    value:Optional[str] = None
    items:Optional[List[LinkDataCell]]
    

class PercentagBarDataCell(FloatDataCell):
    type: CellType = CellType.PERCENTAGE
    colors: Optional[List[str]] = None

# FIXME: validation failing to recognize subclasses of T_DataCell; see notes in genomics_tracks.py
T_TableDataCell = Dict[str, Any] # Dict[str, Union[Type[T_DataCell], int, float, str, bool, None]]