from enum import StrEnum, auto
from typing import Any, Dict, List, Optional, TypeVar, Union

from pydantic import BaseModel

# raw data type cells only, not rendering wrappers
# those should be handled on the front end


class TableCellType(StrEnum):
    BOOLEAN = auto()
    ABSTRACT = auto()
    FLOAT = auto()
    INTEGER = auto()
    PVALUE = "p_value"
    TEXT = auto()
    TEXT_LIST = auto()
    LINK = auto()
    LINK_LIST = auto()

    def __str__(self):
        return self.value.lower()


class TableCell(BaseModel):
    type: TableCellType = TableCellType.ABSTRACT
    value: Any = None


class FloatTableCell(TableCell):
    type: TableCellType = TableCellType.FLOAT
    value: Optional[Union[int, float]] = None
    precision: Optional[int] = 2


class IntegerTableCell(TableCell):
    type: TableCellType = TableCellType.INTEGER
    value: Optional[int] = None


class PValueTableCell(TableCell):
    type: TableCellType = TableCellType.PVALUE
    value: Optional[float] = None
    neg_log10_pvalue: Optional[float] = None


class TextTableCell(TableCell):
    type: TableCellType = TableCellType.TEXT
    value: Optional[str] = None
    truncateTo: Optional[int] = 100
    color: Optional[str] = None
    tooltip: Optional[str] = None


class TextListTableCell(TableCell):
    type: TableCellType = TableCellType.TEXT_LIST
    value: Optional[str] = None
    items: Optional[List[TextTableCell]]


class BooleanTableCell(TableCell):
    type: TableCellType = TableCellType.BOOLEAN
    value: Optional[bool] = None
    displayText: Optional[str] = None


class LinkTableCell(TableCell):
    type: TableCellType = TableCellType.LINK
    url: Optional[str] = None
    value: Optional[str] = None


class LinkListTableCell(TableCell):
    type: TableCellType = TableCellType.LINK_LIST
    value: Optional[str] = None
    items: Optional[List[LinkTableCell]]


T_TableCell = TypeVar("T_TableCell", bound=TableCell)
