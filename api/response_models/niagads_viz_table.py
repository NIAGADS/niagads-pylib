from pydantic import BaseModel
from typing import Optional, List, Dict, Any

from .base_models import BaseResponseModel, SerializableModel

class TableOptions(BaseModel):
    title: Optional[str] = None
    disableColumnFilters: Optional[bool] = False
    defaultColumns: Optional[List[str]] = None
    
class Table(BaseModel):
    id: str
    data: List[Any]
    columns: List[Dict[str, Any]]
    options: TableOptions
    

class TableResponse(BaseResponseModel):
    response: Table
