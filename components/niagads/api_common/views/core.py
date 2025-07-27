from typing import Optional

from niagads.api_common.models.response.pagination import (
    PaginationDataModel,
)
from niagads.api_common.models.response.request import RequestDataModel
from pydantic import BaseModel, Field


class ViewResponse(BaseModel):
    request: RequestDataModel = Field(
        description="details about the originating request that generated the response"
    )
    pagination: Optional[PaginationDataModel] = Field(
        description="pagination details, if the result is paged"
    )
    message: Optional[str] = None
