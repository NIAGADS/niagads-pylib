from abc import ABC, abstractmethod
from pydantic import Field
from typing import Any, Dict, TypeVar
from typing_extensions import Self

from api.common.enums import OnRowSelect, ResponseFormat, ResponseView
from api.models.base_models import PaginationDataModel, RequestDataModel, RowModel, SerializableModel


# FIXME: 'Any' or 'SerializableModel' for response
class AbstractResponse(ABC, SerializableModel):
    response: Any = Field(description="result (data) from the request")
    
    @abstractmethod
    def to_text(self, format:ResponseFormat, **kwargs):
        """ return a text response (e.g., BED, VCF, Download script) """
        raise RuntimeError('`AbstractModel` is an abstract class; need to override abstract methods in child classes')
    
    @abstractmethod 
    def to_view(self, view:ResponseView, **kwargs):
        """ transform response to JSON expected by NIAGADS-viz-js Table """
        raise RuntimeError('`AbstractModel` is an abstract class; need to override abstract methods in child classes')

class BaseResponseModel(AbstractResponse):
    request: RequestDataModel = Field(description="details about the originating request that generated the response")

    def to_view(self, view: ResponseView, **kwargs):
        """ transform response to JSON expected by NIAGADS-viz-js Table """
        if len(self.response) == 0:
            raise RuntimeError('zero-length response; cannot generate view')
        if 'on_row_select' not in kwargs:
            if 'num_overlaps' in self.response[0].model_fields.keys() or \
                'num_overlaps' in self.response[0].model_extra.keys():
                kwargs['on_row_select'] = OnRowSelect.ACCESS_ROW_DATA
                
        viewResponse: Dict[str, Any] = {}
        data = []
        row: RowModel # annotated type hint
        for index, row in enumerate(self.response):
            if index == 0:
                viewResponse = row.get_view_config(view, **kwargs)
            data.append(row.to_view_data(view, **kwargs))
        viewResponse.update({'data': data})
    
        if view == ResponseView.TABLE:
            viewResponse.update({'id': kwargs['id']})
            
        return viewResponse
    
    def to_text(self, format: ResponseFormat, **kwargs):
        """ return a text response (e.g., BED, VCF, Download script) """
        
        responseStr = "" 
        rowText = [] 
        if len(self.response) > 0:
            row: RowModel
            for row in self.response:
                rowText.append(row.to_text(format, **kwargs))        
            responseStr = '\n'.join(rowText)
        
        return responseStr
        
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
    
    
# possibly allows you to set a type hint to a class and all its subclasses
T_BaseResponseModel = TypeVar('T_BaseResponseModle', bound=BaseResponseModel)