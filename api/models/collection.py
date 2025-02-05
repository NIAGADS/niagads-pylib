from sqlmodel import SQLModel
from typing import List

from api.common.enums import ResponseView
from api.models.base_models import GenericDataModel
from api.models.base_response_models import BaseResponseModel


class Collection(SQLModel, GenericDataModel):
    name:str 
    description:str 
    num_tracks: int
    
    def to_view_data(self, view: ResponseView, **kwargs):
        return self.model_dump()
    
    def get_view_config(self, view: ResponseView, **kwargs):
        """ get configuration object required by the view """
        return super().get_view_config(view, **kwargs)
    
    def to_text(self, view: ResponseView, **kwargs):
        return super().to_text(view, **kwargs)
    
class CollectionResponse(BaseResponseModel):
    response: List[Collection]
    
    def to_view(self, view: ResponseView, **kwargs):
        return super().to_view(view, **kwargs)