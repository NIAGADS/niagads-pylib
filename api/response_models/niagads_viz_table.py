from pydantic import BaseModel
from typing import Optional, List, Dict, Any
from fastapi.encoders import jsonable_encoder

class TableOptions(BaseModel):
    title: Optional[str] = None
    disableColumnFilters: Optional[bool] = False
    defaultColumns: Optional[List[str]] = None
    
class Table(BaseModel):
    id: str
    data: List[Dict[str, Any]]
    columns: List[Dict[str, Any]]
    options: TableOptions
    
    def serialize(self, expandObjects=False):
        """Return a dict which contains only serializable fields."""
        return jsonable_encoder(self.model_dump())
        
