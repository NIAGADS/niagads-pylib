from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field

from .base_models import PaginationDataModel, RequestDataModel

class BaseViewResponseModel(BaseModel):
    request: RequestDataModel = Field(description="details about the originating request that generated the response")
    pagination: Optional[PaginationDataModel] = Field(description="pagination details, if the result is paged")

class TableViewModel(BaseModel):
    data: List[Dict[str, Any]]
    columns: List[Dict[str, Any]]
    options: Optional[Dict[str, Any]]
    id: str
    
class TableViewResponseModel(BaseViewResponseModel):
    response: TableViewModel
    
