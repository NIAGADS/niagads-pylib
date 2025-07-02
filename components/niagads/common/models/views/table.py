"""Table View Data and Response Models

FIXME: remove front end rendering and place in configuration JSON
"""

from enum import StrEnum, auto
from typing import Any, Dict, List, Optional, Union

from pydantic import BaseModel, ConfigDict, model_serializer


class TableCellType(StrEnum):
    BOOLEAN = auto()
    ABSTRACT = auto()
    FLOAT = auto()
    INTEGER = auto()
    TEXT = auto()

    def __str__(self):
        return self.value.lower()

    def from_field(self, fieldInfo: Any):
        """infer cell type from from field info"""
        match str(fieldInfo.annotation):
            case s if "str" in s:
                return TableCellType.TEXT
            case s if "bool" in s:
                return TableCellType.BOOLEAN
            case s if "int" in s:
                return TableCellType.INTEGER
            case s if "float" in s:
                return TableCellType.FLOAT
            case _:
                return TableCellType.ABSTRACT


class TableCell(BaseModel):
    value: Optional[Union[str, int, float, bool]] = None
    url: Optional[str] = None
    # items: Optional[List[str]] = None

    @model_serializer()
    def serialize_model(self):
        obj = {"value": self.value}
        if self.url is not None:
            obj.update({"url", self.url})
        # if self.items is not None:
        #     obj.update({"items", self.items})

        return obj


class TableRow(BaseModel):
    __pydantic_extra__: Dict[str, TableCell]
    model_config = ConfigDict(extra="allow")


# FIXME: get columns and options from config files
class TableColumn(BaseModel):
    header: Optional[str] = None
    id: str
    description: Optional[str] = None
    type: Optional[TableCellType] = TableCellType.ABSTRACT


class BaseTable(BaseModel):
    data: List[TableRow]
    columns: List[TableColumn]
