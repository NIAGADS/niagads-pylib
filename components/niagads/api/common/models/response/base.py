from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional, Union

from niagads.api.common.constants import DEFAULT_NULL_STRING
from pydantic import BaseModel, Field


class PaginationDataModel(BaseModel):
    """Captures pagination status."""

    page: int = Field(
        default=1,
        description="if result is paged, indicates the current page of the result; defaults to 1",
    )
    total_num_pages: int = Field(
        default=1,
        description="if the result is paged, reports total number of pages in the full result set (response); defaults to 1",
    )
    paged_num_records: Optional[int] = Field(
        default=None,
        description="number of records in the current paged result set (response)",
    )
    total_num_records: Optional[int] = Field(
        default=None,
        description="total number of records in the full result set (response)",
    )


class AbstractBaseResponse(ABC, BaseModel):
    request: RequestDataModel = Field(
        description="details about the originating request"
    )
    pagination: Optional[PaginationDataModel] = Field(
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

    @abstractmethod
    def to_text(self, incl_header: bool = False, null_str: str = DEFAULT_NULL_STRING):
        """return a plain tab-delimited text reseponse"""
        ...


class MessageResponse(AbstractBaseResponse):
    data: Dict[str, Any]

    def to_text(self, incl_header=False, null_str=DEFAULT_NULL_STRING):
        raise NotImplementedError(
            "`to_text` conversion not implemented for MessageResponse"
        )


class ListResponse(AbstractBaseResponse, TextSerializationMixin):
    data: List[Union[str, int, float]]

    def to_text(self, incl_header=False, null_str=DEFAULT_NULL_STRING):
        return super().to_delimited_text(
            incl_header=incl_header, delimiter="\n", null_str=null_str
        )
