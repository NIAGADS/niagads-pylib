from abc import ABC, abstractmethod
from typing import List, Optional, TypeVar, Union

from niagads.api.common.constants import DEFAULT_NULL_STRING
from niagads.api.common.models.response.pagination import (
    PaginationDataModel,
)
from niagads.api.common.models.response.request import RequestDataModel
from pydantic import BaseModel, Field


class AbstractBaseResponse(BaseModel, ABC):
    data: Union[list, dict]

    def is_empty(self):
        return len(self.data) == 0

    request: RequestDataModel = Field(
        description="details about the originating request"
    )
    pagination: Optional[PaginationDataModel] = Field(
        default=None, description="pagination status, if the result is paged"
    )
    message: Optional[List[str]] = Field(
        default=None, description="warning or info message(s) qualifying the response"
    )

    def is_paged(self):
        return self.pagination is not None

    def add_message(self, msg: str):
        if self.message is None:
            self.message = [msg]
        else:
            self.message.append(msg)

    @abstractmethod
    def to_text(self, incl_header: bool = False, null_str: str = DEFAULT_NULL_STRING):
        """return a plain tab-delimited text reseponse"""
        pass

    @abstractmethod
    def to_table(self, id: str = None, title: str = None):
        """return a table view response"""
        pass

    @abstractmethod
    def to_vcf(self):
        """return a plain-text VCF formatted response"""
        pass

    @abstractmethod
    def to_bed(self):
        """return a plain-text BED formatted response"""
        pass


class MessageResponse(AbstractBaseResponse):
    data: dict = None

    def to_text(self, incl_header=False, null_str="NA"):
        raise NotImplementedError("Not implemented for messages")

    def to_bed(self):
        raise NotImplementedError("Not implemented for messages")

    def to_table(self, id=None, title=None):
        raise NotImplementedError("Not implemented for messages")

    def to_vcf(self):
        raise NotImplementedError("Not implemented for messages")


class ListResponse(AbstractBaseResponse):
    data: List[Union[str, int, float]]

    def to_table(self, id=None, title=None):
        raise NotImplementedError("Table views not available for non-tabular data.")

    def to_bed(self):
        raise NotImplementedError(
            "BED formatted responses not available for non-tabular data."
        )

    def to_vcf(self):
        raise NotImplementedError(
            "VCF formatted responses not available for non-tabular data."
        )

    def to_text(self, incl_header=False, null_str="NA"):
        if self.is_empty():
            return ""

        return "\n".join([null_str if v is None else str(v) for v in self.data])


T_Response = TypeVar("T_Response", bound=AbstractBaseResponse)
