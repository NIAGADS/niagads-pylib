from typing import Any, List, TypeVar

from niagads.api.common.constants import DEFAULT_NULL_STRING
from niagads.api.common.models.core import DynamicRowModel, T_RowModel
from niagads.api.common.models.response.base import AbstractBaseResponse
from niagads.api.common.views.table import Table
from pydantic import Field, model_validator


class RecordResponse(AbstractBaseResponse):

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
