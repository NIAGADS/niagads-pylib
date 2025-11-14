"""Models defining custom types for Response Model class attributes"""

from typing import Dict, List, Union

from fastapi import Request
from niagads.utils.dict import prune
from niagads.utils.string import dict_to_string
from pydantic import BaseModel, Field


class RequestDataModel(BaseModel):
    """Captures cleaned user-centric information about the origining request."""

    request_id: str = Field(description="unique request identifier")
    endpoint: str = Field(description="queried endpoint")
    parameters: Dict[str, Union[int, str, bool]] = Field(
        description="request path and query parameters, includes unspecified defaults"
    )

    def set_request_id(self, id):
        self.request_id = id

    def update_parameters(self, params: BaseModel, exclude: List[str] = []) -> str:
        """add default parameter values that are not included in the originating request"""
        exclude = exclude + [
            "filter"
        ]  # do not overwrite original filter string with parsed tokens
        self.parameters.update(prune(params.model_dump(exclude=exclude)))

    @classmethod
    def sort_query_parameters(cls, params: dict, exclude: bool = False) -> str:
        """called by cache_key method to alphabetize the parameters"""
        if len(params) == 0:
            return ""
        sortedParams = dict(
            sorted(params.items())
        )  # assuming Python 3+ where all dicts are ordered
        if exclude:
            for param in exclude:
                if param in sortedParams:
                    del sortedParams[param]
        return dict_to_string(sortedParams, null_str="null", delimiter="&")

    @classmethod
    async def from_request(cls, request: Request):
        return cls(
            request_id=request.headers.get("X-Request-ID"),
            parameters=dict(request.query_params),
            endpoint=str(request.url.path),
        )
