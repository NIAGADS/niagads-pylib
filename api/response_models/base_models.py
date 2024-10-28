from pydantic import BaseModel, ConfigDict
from typing import Any, Dict, Optional, Union
from typing_extensions import Self
from fastapi.encoders import jsonable_encoder
from fastapi import Request
from urllib.parse import parse_qs
class SerializableModel(BaseModel):
    def serialize(self, promoteObjs=False, collapseUrls=False, groupExtra=False):
        """Return a dict which contains only serializable fields.
        promoteObjs -> when True expands JSON fields; i.e., ds = {a:1, b:2} becomes a:1, b:2 and ds gets dropped
        collapseUrls -> looks for field and field_url pairs and then updates field to be {url: , value: } object
        groupExtra -> if extra fields are present, group into a JSON object
        """
        data:dict = jsonable_encoder(self.model_dump()) # FIXME: not sure if encoder is necessary; check dates? maybe
        if promoteObjs:
            objFields = [ k for k, v in data.items() if isinstance(v, dict)]
            for f in objFields:
                data.update(data.pop(f, None))

        if collapseUrls:
            fields = list(data.keys())
            pairedFields = [ f for f in fields if f + '_url' in fields]
            for f in pairedFields:
                data.update({f: {'url': data.pop(f +'_url', None), 'value': data[f]}})

        if groupExtra:
            raise NotImplementedError()  
        return data
    
    def has_extras(self):
        """ test if extra model fields are present """
        return len(self.model_extra) > 0

class RequestDataModel(SerializableModel):
    request_id: str
    endpoint: str
    parameters: Dict[str, Union[int, str, bool]]
    msg: Optional[str] = None
    
    @classmethod
    async def from_request(cls, request: Request):
        return cls(
            request_id=request.headers.get("X-Request-ID"),
            parameters={k: v[0] for k, v in parse_qs(str(request.query_params)).items()},
            endpoint=str(request.url.path)
        )
    
class BaseResponseModel(SerializableModel):
    request: RequestDataModel
    response: Any
    # TODO: session/user_id?
    
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


class GenericDataModel(SerializableModel):
    """ Generic JSON Response """
    __pydantic_extra__: Dict[str, Any]  
    model_config = ConfigDict(extra='allow')
    
    
class PaginationDataModel(BaseModel):
    page: int = 1
    total_num_pages: int = 1
    paged_num_records: int 
    total_num_records: int

class PagedResponseModel(BaseResponseModel):
    pagination: Optional[PaginationDataModel] = None
    