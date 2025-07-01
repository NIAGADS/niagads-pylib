from abc import ABC, abstractmethod
from typing import List, Optional, TypeVar

from niagads.open_access_api_common.config.constants import DEFAULT_NULL_STRING
from niagads.open_access_api_common.models.records.core import RowModel, T_RowModel
from niagads.open_access_api_common.models.response.pagination import (
    PaginationDataModel,
)
from niagads.open_access_api_common.models.response.request import RequestDataModel
from niagads.open_access_api_common.models.views.table.core import TableViewModel
from pydantic import BaseModel, Field


class AbstractResponse(BaseModel, ABC):

    @abstractmethod
    def to_text(self, inclHeader: bool = False, nullStr: str = DEFAULT_NULL_STRING):
        """return a plain tab-delimited text reseponse"""
        pass

    @abstractmethod
    def to_table(self, id: str = None, title: str = None):
        """return a table view response"""
        pass

    @abstractmethod
    def to_vcf(self, inclHeader: bool = False):
        """return a plain-text VCF formatted response"""
        pass

    @abstractmethod
    def to_bed(self, inclHeader: bool = False):
        """return a plain-text BED formatted response"""
        pass


class GenericResponse(AbstractResponse):

    data: List[RowModel] = Field(description="query result")
    request: RequestDataModel = Field(
        description="details about the originating request"
    )
    pagination: Optional[PaginationDataModel] = Field(
        default=None, description="pagination status, if the result is paged"
    )
    message: Optional[List[str]] = Field(
        default=None, description="warning or info message(s) qualifying the response"
    )

    def is_empty(self):
        return len(self.data) == 0

    def is_paged(self):
        return self.pagination is not None

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

    def add_message(self, msg: str):
        if self.message is None:
            self.message = [msg]
        else:
            self.message.append(msg)

    # START abstract methods

    def to_table(self, id: str = None, title: str = None):
        model: T_RowModel = self.row_model()

        if self.is_empty():
            return {}

        else:
            columns = model.table_columns()
            data = [r.as_table_row() for r in self.data]
            table = {"columns": columns, "data": data}

            if title is not None:
                table.update({"title", title})
            if id is not None:
                table.update({"id": id})
            return TableViewModel(**table)

    def to_vcf(self, inclHeader=False):
        raise NotImplementedError(
            "VCF formatted output not available for a generic data response."
        )

    def to_bed(self, inclHeader=False):
        raise NotImplementedError(
            "BED formatted output not available for a generic data repsonse."
        )

    def to_text(self, inclHeader=False, nullStr: str = DEFAULT_NULL_STRING):

        if self.is_empty():
            return ""

        else:
            # not sure if this check will still be necessary
            # if isinstance(self.data, dict):
            #    if inclHeader:
            #       responseStr = "\t".join(list(self.data.keys())) + "\n"
            #    responseStr += (
            #        "\t".join([xstr(v, nullStr=nullStr) for v in self.data.values()]) + "\n"
            #    )

            model: T_RowModel = self.row_model()
            fields = model.get_fields(asStr=True)

            rows = []
            for r in self.data:
                if isinstance(r, str):
                    rows.append(r)
                else:
                    # pass fields to ensure consistent ordering
                    rows.append("\t".join(r.as_text(fields=fields, nullStr=nullStr)))

            responseStr = "\t".join(fields) + "\n" if inclHeader else ""
            responseStr += "\n".join(rows)

        return responseStr

    # END abstract methods


# possibly allows you to set a type hint to a class and all its subclasses
T_GenericResponse = TypeVar("T_GenericResponse", bound=GenericResponse)
