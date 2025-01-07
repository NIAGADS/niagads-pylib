from pydantic import Field
from typing import TypeVar
from typing_extensions import Self

from api.models.base_models import AbstractResponse, PaginationDataModel, RequestDataModel

class BaseResponseModel(AbstractResponse):
    request: RequestDataModel = Field(description="details about the originating request that generated the response")

    def to_view(self, view, **kwargs):
        return super().to_view(view, **kwargs)
        
    @classmethod
    def row_model(cls: Self, name=False):
        """ get the type of the row model in the response """
        
        rowType = cls.model_fields['response'].annotation
        try: # can't explicity test for List[rowType], so just try
            rowType = rowType.__args__[0] # rowType = typing.List[RowType]
        except:
            rowType = rowType
        
        return rowType.__name__ if name == True else rowType
    
    @classmethod
    def is_paged(cls: Self):
        return 'pagination' in cls.model_fields

class PagedResponseModel(BaseResponseModel):
    pagination: PaginationDataModel = Field(description="pagination details, if the result is paged")

    def to_view(self, view, **kwargs):
        return super().to_view(view, **kwargs)

# possibly allows you to set a type hint to a class and all its subclasses
T_BaseResponseModel = TypeVar('T_BaseResponseModle', bound=BaseResponseModel)