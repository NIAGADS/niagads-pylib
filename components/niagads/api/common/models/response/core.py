from abc import ABC, abstractmethod
from typing import Any, List, Optional, TypeVar, Union

from niagads.api.common.constants import DEFAULT_NULL_STRING
from niagads.api.common.models.core import DynamicRowModel, T_RowModel
from niagads.api.common.models.response.pagination import (
    PaginationDataModel,
)
from niagads.api.common.models.response.request import RequestDataModel
from niagads.api.common.views.table import Table
from pydantic import BaseModel, Field, model_validator


class AbstractResponse(BaseModel, ABC):
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


class MessageResponse(AbstractResponse):
    data: dict = None

    def to_text(self, incl_header=False, null_str="NA"):
        raise NotImplementedError("Not implemented for messages")

    def to_bed(self):
        raise NotImplementedError("Not implemented for messages")

    def to_table(self, id=None, title=None):
        raise NotImplementedError("Not implemented for messages")

    def to_vcf(self):
        raise NotImplementedError("Not implemented for messages")


class ListResponse(AbstractResponse):
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


class RecordResponse(AbstractResponse):

    data: List[T_RowModel] = Field(
        description="a list of one or more records or data points; format of list entries will vary by the resource and type of record or data being queried by the endpoint"
    )

    @model_validator(mode="before")
    @classmethod
    def validate_row_model(cls, data: Any):
        # wrong serialization
        if isinstance(data, str):
            return data
        if isinstance(data, dict):
            return data

        if isinstance(data, list):
            if not isinstance(data[0], dict):
                return cls(data=data)  # assume T_RowModel
            return cls(data=[DynamicRowModel(**item) for item in data])

    @classmethod
    def row_model(cls, name=False):
        """get the type of the row model in the response;
        if name is True, return the class name, otherwise
        return the type"""

        rowType = cls.model_fields["data"].annotation
        try:  # can't explicity test for List[rowType], so just try
            rowType = rowType.__args__[0]  # rowType = typing.List[RowType]
        except:
            rowType = rowType

        return rowType.__name__ if name == True else rowType

    # START abstract methods

    def to_table(self, id: str = None, title: str = None):
        if self.is_empty():
            return {}

        else:
            columns = self.data[0].generate_table_columns()
            data = [r.as_table_row() for r in self.data]
            table = {"columns": columns, "data": data}

            if title is not None:
                table.update({"title", title})
            if id is not None:
                table.update({"id": id})
            return Table(**table)

    def to_vcf(self):
        raise NotImplementedError(
            "VCF formatted output not available for a generic data response."
        )

    def to_bed(self):
        raise NotImplementedError(
            "BED formatted output not available for a generic data repsonse."
        )

    def _get_empty_header(self):
        model: T_RowModel = self.row_model()
        fields = model.get_model_fields(as_str=True)
        return "\t".join(fields) + "\n"

    def to_text(self, incl_header=False, null_str: str = DEFAULT_NULL_STRING):
        if self.is_empty():
            if incl_header:
                # no data so have to get model fields from the class
                return self._get_empty_header()
            else:
                return ""

        else:
            # not sure if this check will still be necessary
            # if isinstance(self.data, dict):
            #    if incl_header:
            #       responseStr = "\t".join(list(self.data.keys())) + "\n"
            #    responseStr += (
            #        "\t".join([xstr(v, null_str=null_str) for v in self.data.values()]) + "\n"
            #    )

            fields = self.data[0].get_table_fields(as_str=True)
            rows = []
            for r in self.data:
                if isinstance(r, str):
                    rows.append(r)
                else:
                    # pass fields to ensure consistent ordering
                    rows.append(r.as_text(fields=fields, null_str=null_str))

            responseStr = "\t".join(fields) + "\n" if incl_header else ""
            responseStr += "\n".join(rows)

        return responseStr

    # END abstract methods


# possibly allows you to set a type hint to a class and all its subclasses
T_RecordResponse = TypeVar("T_RecordResponse", bound=RecordResponse)
T_Response = TypeVar("T_Response", bound=AbstractResponse)
