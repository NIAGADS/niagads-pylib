from typing import Any, Dict, Optional, Union

from niagads.api.common.constants import DEFAULT_NULL_STRING
from niagads.api.common.models.context.request import RequestDetails
from niagads.api.common.models.responses.pagination import PaginationState
from niagads.common.models.base import CustomBaseModel
from pydantic import Field


class BaseResponseModel(CustomBaseModel):
    request: RequestDetails = Field(description="details about the originating request")
    pagination: Optional[PaginationState] = Field(
        default=None, description="pagination status, if the result is paged"
    )
    message: Optional[list[Union[str, dict]]] = Field(
        default=None, description="warning or info message(s) qualifying the response"
    )

    @property
    def is_empty(self):
        return len(self.data) == 0

    @property
    def is_paged(self):
        return self.pagination is not None

    def update_message(self, msg: Union[str, dict]):
        if self.message is None:
            self.message = [msg]
        else:
            self.message.append(msg)


class MessageResponse(BaseResponseModel):
    data: Dict[str, Any]

    def to_delimited_text(self, incl_header=False, null_str=DEFAULT_NULL_STRING):
        raise NotImplementedError(
            "`to_delimited_text` conversion not implemented for MessageResponse"
        )
