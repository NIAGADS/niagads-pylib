from pydantic import BaseModel
from typing import Optional, List, Dict, Union, Any
from fastapi.encoders import jsonable_encoder
from fastapi import Request

class SerializableModel(BaseModel):
    def serialize(self, expandObjs=False):
        """Return a dict which contains only serializable fields."""
        data:dict = jsonable_encoder(self.model_dump())
        if expandObjs:
            for k,v in data.items():
                if isinstance(v, dict):
                    data.update(k, data.pop(k, None))
        return data

class RequestDataModel(BaseModel):
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