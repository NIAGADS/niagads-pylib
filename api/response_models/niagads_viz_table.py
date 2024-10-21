from pydantic import BaseModel
from typing import Optional, List

class TableOptions(BaseModel):
    title: Optional[str]
    disableColumnFilters: Optional[bool]
    defaultColumns: Optional[List[str]]
    
class Table(BaseModel):
    id: str
    data: List[dict]
    columns: List[dict]
    options: TableOptions