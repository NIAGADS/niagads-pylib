from sqlmodel import SQLModel
from typing import List

from api.common.enums.response_properties import ResponseView
from api.models.base_response_models import BaseResponseModel
from api.models.base_row_models import GenericDataModel, RowModel

class Collection(SQLModel, RowModel):
    name:str 
    description:str 
    num_tracks: int
    
    def to_view_data(self, view: ResponseView, **kwargs):
        return self.model_dump()
    
class CollectionResponse(BaseResponseModel):
    response: List[Collection]
    