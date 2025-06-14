from typing import Any, Dict, Optional, TypeVar

from niagads.open_access_api_common.config.constants import DEFAULT_NULL_STRING
from niagads.open_access_api_common.models.response.pagination import (
    PaginationDataModel,
)
from niagads.open_access_api_common.models.response.request import RequestDataModel
from niagads.open_access_api_common.parameters.response import (
    ResponseFormat,
    ResponseView,
)
from niagads.utils.string import xstr
from pydantic import BaseModel, Field
from typing_extensions import Self


class GenericResponse(BaseModel):

    data: Any = Field(description="result (data) from the request")
    request: RequestDataModel = Field(
        description="details about the originating request that generated the response"
    )
    pagination: Optional[PaginationDataModel] = Field(
        default=None, description="pagination details, if the result is paged"
    )

    def has_count_fields(self):
        if any(
            f.startswith("num_") for f in self.data[0].__class__.model_fields.keys()
        ):
            return True
        if isinstance(self.data[0].model_extra, dict):
            return any(f.startswith("num_") for f in self.data[0].model_extra.keys())

    @classmethod
    def is_paged(self: Self):
        return self.pagination is not None

    @classmethod
    def row_model(cls: Self, name=False):
        """get the type of the row model in the response"""

        rowType = cls.model_fields["data"].annotation
        try:  # can't explicity test for List[rowType], so just try
            rowType = rowType.__args__[0]  # rowType = typing.List[RowType]
        except:
            rowType = rowType

        return rowType.__name__ if name == True else rowType

    def add_message(self, str):
        self.request.add_message(str)

    def to_view(self, view: ResponseView, **kwargs):
        # avoid circular imports
        from niagads.open_access_api_common.models.records.core import RowModel
        from niagads.open_access_api_common.models.views.table.core import (
            TableViewModel,
        )

        if len(self.data) == 0:
            raise RuntimeError("zero-length response; cannot generate view")

        # FIXME: move to front end
        # if self.has_count_fields():
        #     kwargs["on_row_select"] = OnRowSelect.ACCESS_ROW_DATA

        viewResponse: Dict[str, Any] = {}
        data = []
        row: RowModel  # annotated type hint
        for index, row in enumerate(self.data):
            if index == 0:
                viewResponse = row.get_view_config(view, **kwargs)
                # if not isinstance(viewResponse["columns"][0], TableColumn):
                #     kwargs["field_names"] = [c["id"] for c in viewResponse["columns"]]
            kwargs["fields"] = [c.id for c in viewResponse["columns"]]
            data.append(row.to_view_data(view, **kwargs))
        viewResponse.update({"data": data})

        match view:
            case ResponseView.TABLE:
                viewResponse.update({"id": kwargs["id"]})
                return TableViewModel(**viewResponse)
            case ResponseView.IGV_BROWSER:
                raise NotImplementedError("IGVBrowser view coming soon")
            case _:
                raise RuntimeError(f"Invalid view: {view}")

        return viewResponse

    def to_text(self, format: ResponseFormat, **kwargs):
        """return a text response (e.g., BED, VCF, plain text)"""
        from niagads.open_access_api_common.models.records.core import RowModel

        nullStr = kwargs.get("nullStr", DEFAULT_NULL_STRING)
        if isinstance(self.data, dict):
            responseStr = "\t".join(list(self.data.keys())) + "\n"
            responseStr += (
                "\t".join([xstr(v, nullStr=nullStr) for v in self.data.values()]) + "\n"
            )
        else:
            header = kwargs.get("fields", None)
            responseStr = "" if header is None else "\t".join(header) + "\n"
            rowText = []
            if len(self.data) > 0:
                for row in self.data:
                    if isinstance(row, str):
                        rowText.append(row)
                    else:
                        row: RowModel
                        rowText.append(row.to_text(format, **kwargs))
            responseStr += "\n".join(rowText)

        return responseStr


# possibly allows you to set a type hint to a class and all its subclasses
T_GenericResponse = TypeVar("T_GenericResponse", bound=GenericResponse)
