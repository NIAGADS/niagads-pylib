from pydantic import BaseModel
from typing import Optional, List, Dict, Union, Any
from fastapi.encoders import jsonable_encoder
from fastapi import Request

class SerializableModel(BaseModel):
    def serialize(self, expandObjs=False, collapseUrls=False):
        """Return a dict which contains only serializable fields.
        expandObjs -> when True expands JSON fields; i.e., ds = {a:1, b:2} becomes a:1, b:2 and ds gets dropped
        collapseUrls -> looks for field and field_url pairs and then updates field to be {url: , value: } object
        """
        data:dict = jsonable_encoder(self.model_dump())
        if expandObjs:
            objFields = [ k for k, v in data.items() if isinstance(v, dict)]
            for f in objFields:
                data.update(data.pop(f, None))

        if collapseUrls:
            fields = list(data.keys())
            pairedFields = [ f for f in fields if f + '_url' in fields]
            for f in pairedFields:
                data.update({f: {'url': data.pop(f +'_url', None), 'value': data[f]}})
            
        return data

class RequestDataModel(SerializableModel, BaseModel):
    request_id: str
    endpoint: str
    parameters: str
    
    @classmethod
    async def from_request(cls, request: Request):
        return cls(
            request_id=request.headers.get("X-Request-ID"),
            parameters=str(request.query_params),
            endpoint=str(request.url.path)
        )
    
class BaseResponseModel(SerializableModel, BaseModel):
    request: RequestDataModel
    response: Any
    # TODO: session/user_id?

class PagedResponseModel(BaseResponseModel):
    page: int 
    total_num_pages: int 