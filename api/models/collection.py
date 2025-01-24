from sqlmodel import SQLModel
from typing import List

from api.models.base_models import RowModel
from api.models.base_response_models import BaseResponseModel


class Collection(SQLModel, RowModel):
    name:str 
    description:str 
    num_tracks: int
    
    def to_view_data(self, view, **kwargs):
        return self.model_dump()
    
    def get_view_config(self, view, **kwargs):
        """ get configuration object required by the view """
        return super().get_view_config(view, **kwargs)
    
class CollectionResponse(BaseResponseModel):
    response: List[Collection]
    
    def to_view(self, view, **kwargs):
        return super().to_view(view, **kwargs)