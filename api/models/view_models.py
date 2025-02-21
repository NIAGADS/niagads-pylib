
from enum import StrEnum
from typing import Any, Dict, List, Optional, Type, TypeVar, Union
from pydantic import BaseModel, Field, model_serializer

from niagads.utils.dict import prune

from api.models.base_models import NullFreeModel
from api.models.response_model_properties import PaginationDataModel, RequestDataModel

TableCell = StrEnum('TableCell', ["boolean", "abstract", "float", "p_value", "text", "annotated_text", "badge", "link", "percentage_bar"])
class BadgeIcon(StrEnum):
    CHECK = 'check'
    SOLID_CHECK = 'solidCheck'
    INFO = 'info'
    WARNING = 'warning'
    USER = 'user'
    INFO_OUTLINE = 'infoOutline'
    X_MARK = 'xMark'    


class BaseViewResponseModel(BaseModel):
    request: RequestDataModel = Field(description="details about the originating request that generated the response")
    pagination: Optional[PaginationDataModel] = Field(description="pagination details, if the result is paged")

class TableColumn(NullFreeModel):
    header: Optional[str] = None
    id: str
    description: Optional[str] = None
    type: Optional[TableCell] = "abstract"
    canFilter: Optional[bool] = None
    disableGlobalFilter: Optional[bool] = None
    disableSorting: Optional[bool] = None
    required: Optional[bool] = None

    
class DataCell(NullFreeModel):
    type:str = "abstract"
    value: Optional[Union[str, bool, int, float]] = None
    # nullValue: Optional[str] = None
    # naValue: Optional[str] = 'NA'


T_DataCell = TypeVar('T_DataCell', bound=DataCell)

class FloatDataCell(DataCell):
    type:str = "float"
    value: Optional[Union[int, float]] = None
    precision: Optional[int] = 2
    
class PValueDataCell(FloatDataCell):
    # type:str = "p_value"
    type: str = "float"
    value:Optional[float] = None
    neg_log10_pvalue: Optional[float] = None

class TextDataCell(DataCell):
    type:str = "text"
    value:Optional[str] = None
    truncateTo:Optional[int] = 100
    color: Optional[str] = None
    tooltip: Optional[str] = None

class TextListDataCell(DataCell):
    type:str = "text_list",
    value:Optional[str] = None
    items: Optional[List[TextDataCell]]

class BadgeDataCell(TextDataCell):
    type:str = "badge"
    backgroundColor:Optional[str] = None
    borderColor: Optional[str] = None
    icon: Optional[BadgeIcon] = None

class BooleanDataCell(BadgeDataCell):
    type:str = "boolean"
    value:Optional[bool] = None
    displayText: Optional[Union[str, bool]] = None
    
class LinkDataCell(DataCell):
    type:str = "link"
    url:Optional[str] = None
    tooltip: Optional[str] = None
    
class LinkListDataCell(DataCell):
    type:str = "link_list"
    value:Optional[str] = None
    items:Optional[List[LinkDataCell]]
    

class PercentagBarDataCell(FloatDataCell):
    type:str = "percentage_bar"
    colors: Optional[List[str]] = None

# FIXME: validation failing to recognize subclasses of T_DataCell; see notes in genomics_tracks.py
TABLE_DATA_CELL = Dict[str, Any] # Dict[str, Union[Type[T_DataCell], int, float, str, bool, None]]

class TableViewModel(BaseModel, arbitrary_types_allowed=True):
    data: List[TABLE_DATA_CELL]
    columns: List[TableColumn]
    options: Optional[Dict[str, Any]] = None
    id: str
    
class TableViewResponse(BaseViewResponseModel):
    
    response: TableViewModel
    
