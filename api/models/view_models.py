
from typing import Any, Dict, List, Optional
from pydantic import BaseModel


class Table(BaseModel):
    data: List[Dict[str, Any]]
    columns: List[Dict[str, Any]]
    options: Optional[Dict[str, Any]]
    id: str